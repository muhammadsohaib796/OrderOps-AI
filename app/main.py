from fastapi import FastAPI
from app.graph.graph import graph

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

    return {"order_id": order_id, "final_status": result["final_status"]}