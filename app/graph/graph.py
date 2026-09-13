from langgraph.checkpoint.postgres import PostgresSaver
import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from app.graph.state import OrderState
from app.database import SessionLocal
from app.models import Order, Customer, OrderItem, Product, NegotiationOffer

load_dotenv()


def fraud_check(state: OrderState) -> OrderState:
    print(f"[fraud_check] Checking order {state['order_id']}")
    db = SessionLocal()
    try:
        order = db.get(Order, state["order_id"])
        customer = db.get(Customer, order.customer_id)
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()

        order_total = sum(
            item.quantity * db.get(Product, item.product_id).price
            for item in items
        )

        risk_score = 0.0
        if order_total > 100:
            risk_score += 0.4
        if not customer.phone:
            risk_score += 0.3
        if any(item.quantity > 5 for item in items):
            risk_score += 0.3

        risk_score = min(risk_score, 1.0)

        state["risk_score"] = risk_score
        state["is_flagged"] = risk_score > 0.7
        print(f"[fraud_check] order_total={order_total}, risk_score={risk_score}")
    finally:
        db.close()
    return state


def inventory_check(state: OrderState) -> OrderState:
    print(f"[inventory_check] Checking stock for order {state['order_id']}")
    db = SessionLocal()
    try:
        items = db.query(OrderItem).filter(OrderItem.order_id == state["order_id"]).all()
        out_of_stock = []
        for item in items:
            product = db.get(Product, item.product_id)
            if product.stock_quantity < item.quantity:
                out_of_stock.append(product.id)
        state["out_of_stock_items"] = out_of_stock
        print(f"[inventory_check] out_of_stock_items={out_of_stock}")
    finally:
        db.close()
    return state


def find_alternative_product(db, out_of_stock_product: Product) -> Product | None:
    STOPWORDS = {"limited", "edition", "standard", "the", "a", "of"}
    target_words = set(out_of_stock_product.name.lower().split()) - STOPWORDS

    candidates = (
        db.query(Product)
        .filter(Product.id != out_of_stock_product.id, Product.stock_quantity > 0)
        .all()
    )

    for candidate in candidates:
        candidate_words = set(candidate.name.lower().split()) - STOPWORDS
        if target_words & candidate_words:
            return candidate
    return None


def negotiate(state: OrderState) -> OrderState:
    print(f"[negotiate] Offering alternative for order {state['order_id']}")
    db = SessionLocal()
    try:
        # For now, handle the first out-of-stock item — multi-item negotiation is a later concern
        original_product_id = state["out_of_stock_items"][0]
        original_product = db.get(Product, original_product_id)

        alternative = find_alternative_product(db, original_product)

        offer = NegotiationOffer(
            order_id=state["order_id"],
            original_product_id=original_product.id,
            alternative_product_id=alternative.id if alternative else None,
            discount_percent=10.0,
            status="offered",
        )
        db.add(offer)
        db.commit()

        if alternative:
            state["alternative_product_id"] = alternative.id
            print(f"[negotiate] Offered '{alternative.name}' (10% off) in place of '{original_product.name}'")
        else:
            state["alternative_product_id"] = None
            print(f"[negotiate] No alternative found for '{original_product.name}'")
    finally:
        db.close()
    return state

def route_after_negotiate(state: OrderState) -> str:
    return "await_response" if state["alternative_product_id"] is not None else "finalize"


def await_response(state: OrderState) -> OrderState:
    print(f"[await_response] Waiting on customer for order {state['order_id']}")
    return state


def finalize(state: OrderState) -> OrderState:
    print(f"[finalize] Wrapping up order {state['order_id']}")
    if state.get("customer_response") == "accepted":
        state["final_status"] = "updated"
    elif state["out_of_stock_items"]:
        state["final_status"] = "refunded"
    else:
        state["final_status"] = "fulfilled"
    return state


def route_after_fraud(state: OrderState) -> str:
    return "flagged" if state["is_flagged"] else "continue"


def route_after_inventory(state: OrderState) -> str:
    return "negotiate" if state["out_of_stock_items"] else "fulfill"


builder = StateGraph(OrderState)

builder.add_node("fraud_check", fraud_check)
builder.add_node("inventory_check", inventory_check)
builder.add_node("negotiate", negotiate)
builder.add_node("await_response", await_response)
builder.add_node("finalize", finalize)

builder.set_entry_point("fraud_check")

builder.add_conditional_edges(
    "fraud_check",
    route_after_fraud,
    {
        "flagged": END,
        "continue": "inventory_check",
    },
)

builder.add_conditional_edges(
    "inventory_check",
    route_after_inventory,
    {
        "negotiate": "negotiate",
        "fulfill": "finalize",
    },
)

builder.add_conditional_edges(
    "negotiate",
    route_after_negotiate,
    {
        "await_response": "await_response",
        "finalize": "finalize",
    },
)
builder.add_edge("await_response", "finalize")
builder.add_edge("finalize", END)



DATABASE_URL = os.getenv("DATABASE_URL")

checkpointer_cm = PostgresSaver.from_conn_string(DATABASE_URL)
checkpointer = checkpointer_cm.__enter__()
checkpointer.setup()

graph = builder.compile(checkpointer=checkpointer, interrupt_before=["await_response"])