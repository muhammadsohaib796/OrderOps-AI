from fastapi import FastAPI
from app.graph.graph import graph
from app.database import SessionLocal
from app.models import Order, NegotiationOffer, OrderStatus
from datetime import datetime


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