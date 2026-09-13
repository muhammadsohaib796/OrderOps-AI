from app.graph.graph import graph

initial_state = {
    "order_id": 1,
    "customer_id": 1,
    "risk_score": None,
    "is_flagged": False,
    "out_of_stock_items": [],
    "alternative_product_id": None,
    "customer_response": None,
    "final_status": None,
}

result = graph.invoke(initial_state)
print("\nFinal state:", result)