from app.graph.graph import graph

config = {"configurable": {"thread_id": "1"}}  # thread_id must be a string

initial_state = {
    "order_id": 1,
    "customer_id": 1,
    "risk_score": None,
    "is_flagged": False,
    "out_of_stock_items": [],
    "alternative_product_id": {},
    "customer_response": None,
    "final_status": None,
}

result = graph.invoke(initial_state, config=config)
print("\nState after first invoke (should be PAUSED before await_response):", result)