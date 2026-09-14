from fastapi import FastAPI
from app.graph.graph import graph
from app.database import SessionLocal
from app.models import Order, NegotiationOffer, OrderStatus
from datetime import datetime

from app.schemas import OrderCreate
from app.models import OrderItem

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "OrderOps AI is running"}


@app.get("/respond")
def respond_to_offer(order_id: int, decision: str):
    if decision not in ("accept", "decline"):
        return {"error": "decision must be 'accept' or 'decline'"}

    config = {"configurable": {"thread_id": str(order_id)}}

    graph.update_state(config, {"customer_response": "accepted" if decision == "accept" else "declined"})

    result = graph.invoke(None, config=config)


    # Reflect the outcome in the real database, not just the graph checkpoint
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
            "alternative_product_id": None,
            "customer_response": None,
            "final_status": None,
        }
        result = graph.invoke(initial_state, config=config)

        return {"order_id": new_order.id, "graph_result": result}
    finally:
        db.close()