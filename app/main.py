from fastapi import FastAPI, HTTPException
from app.graph.graph import graph
from app.database import SessionLocal
from app.models import Order, OrderItem, OrderStatus, Customer, Product, NegotiationOffer
from datetime import datetime

from app.schemas import OrderCreate, CustomerCreate, DemoOrderCreate
from app.models import OrderItem

from fastapi.responses import FileResponse, RedirectResponse    
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")

@app.get("/health")
def health_check():
    return {"status": "OrderOps AI is running"}


@app.get("/respond")
def respond_to_offer(order_id: int, decision: str):
    if decision not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="decision must be 'accept' or 'decline'")

    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    finally:
        db.close()

    config = {"configurable": {"thread_id": str(order_id)}}
    graph.update_state(config, {"customer_response": "accepted" if decision == "accept" else "declined"})
    result = graph.invoke(None, config=config)

    db = SessionLocal()
    try:
        offer = (
            db.query(NegotiationOffer)
            .filter(NegotiationOffer.order_id == order_id)
            .order_by(NegotiationOffer.id.desc())
            .first()
        )
        if offer:
            offer.status = "accepted" if decision == "accept" else "declined"
            offer.responded_at = datetime.utcnow()

        order = db.get(Order, order_id)
        if order:
            order.status = (
                OrderStatus.updated if result["final_status"] == "updated" else OrderStatus.refunded
            )

        db.commit()
    finally:
        db.close()

    return {"order_id": order_id, "final_status": result["final_status"]}


@app.post("/orders")
def create_order(order_data: OrderCreate):
    db = SessionLocal()
    try:
        customer = db.get(Customer, order_data.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail=f"Customer {order_data.customer_id} not found")

        if not order_data.items:
            raise HTTPException(status_code=400, detail="Order must contain at least one item")

        for item in order_data.items:
            product = db.get(Product, item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            if item.quantity < 1:
                raise HTTPException(status_code=400, detail=f"Quantity must be at least 1 (product {item.product_id})")

        new_order = Order(customer_id=order_data.customer_id, status=OrderStatus.pending)
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        for item in order_data.items:
            db.add(OrderItem(order_id=new_order.id, product_id=item.product_id, quantity=item.quantity))
        db.commit()

        config = {"configurable": {"thread_id": str(new_order.id)}}
        initial_state = {
            "order_id": new_order.id,
            "customer_id": new_order.customer_id,
            "risk_score": None,
            "is_flagged": False,
            "out_of_stock_items": [],
            "alternative_products": {},
            "customer_response": None,
            "final_status": None,
        }
        result = graph.invoke(initial_state, config=config)

        return {"order_id": new_order.id, "graph_result": result}
    finally:
        db.close()


@app.get("/orders")
def list_orders():
    db = SessionLocal()
    try:
        orders = db.query(Order).order_by(Order.id.desc()).all()
        return [
            {
                "id": o.id,
                "customer_id": o.customer_id,
                "customer_name": db.get(Customer, o.customer_id).name,
                "status": o.status.value,
                "risk_score": o.risk_score,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ]
    finally:
        db.close()


@app.get("/orders/{order_id}")
def get_order_detail(order_id: int):
    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        offers = db.query(NegotiationOffer).filter(NegotiationOffer.order_id == order_id).all()

        return {
            "id": order.id,
            "customer_id": order.customer_id,
            "customer_name": db.get(Customer, order.customer_id).name,
            "status": order.status.value,
            "risk_score": order.risk_score,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {
                    "product_id": i.product_id,
                    "quantity": i.quantity,
                    "name": db.get(Product, i.product_id).name,
                    "price": db.get(Product, i.product_id).price,
                }
                for i in items
            ],
            "negotiation_offers": [
                {
                    "original_product_id": off.original_product_id,
                    "alternative_product_id": off.alternative_product_id,
                    "discount_percent": off.discount_percent,
                    "alternative_product_name": (
                        db.get(Product, off.alternative_product_id).name
                        if off.alternative_product_id else None
                    ),
                    "discount_percent": off.discount_percent,
                    "status": off.status,
                    "created_at": off.created_at.isoformat() if off.created_at else None,
                    "responded_at": off.responded_at.isoformat() if off.responded_at else None,
                }
                for off in offers
            ],
        }
    finally:
        db.close()

@app.post("/customers")
def create_customer(customer_data: CustomerCreate):
    db = SessionLocal()
    try:
        existing = db.query(Customer).filter(Customer.email == customer_data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Customer with email {customer_data.email} already exists")

        new_customer = Customer(
            name=customer_data.name,
            email=customer_data.email,
            phone=customer_data.phone,
        )
        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)

        return {"id": new_customer.id, "name": new_customer.name, "email": new_customer.email}
    finally:
        db.close()




@app.post("/demo-order")
def create_demo_order(demo_data: DemoOrderCreate):
    """
    One-click demo: find-or-create a customer, then place an order for the
    Limited Edition Hoodie (always out of stock in seed data), guaranteeing
    the full negotiation + email flow triggers.
    """
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.email == demo_data.email).first()
        if not customer:
            customer = Customer(name=demo_data.name, email=demo_data.email, phone=None)
            db.add(customer)
            db.commit()
            db.refresh(customer)

        DEMO_PRODUCT_ID = 2  # Limited Edition Hoodie — kept permanently out of stock for demos

        new_order = Order(customer_id=customer.id, status=OrderStatus.pending)
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        db.add(OrderItem(order_id=new_order.id, product_id=DEMO_PRODUCT_ID, quantity=1))
        db.commit()

        config = {"configurable": {"thread_id": str(new_order.id)}}
        initial_state = {
            "order_id": new_order.id,
            "customer_id": new_order.customer_id,
            "risk_score": None,
            "is_flagged": False,
            "out_of_stock_items": [],
            "alternative_products": {},
            "customer_response": None,
            "final_status": None,
        }
        result = graph.invoke(initial_state, config=config)

        return {
            "order_id": new_order.id,
            "customer_id": customer.id,
            "email_sent_to": demo_data.email,
            "graph_result": result,
        }
    finally:
        db.close()



app.mount("/dashboard", StaticFiles(directory="app/static", html=True), name="dashboard")