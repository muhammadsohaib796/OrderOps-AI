from langgraph.graph import StateGraph, END
from app.graph.state import OrderState


def fraud_check(state: OrderState) -> OrderState:
    print(f"[fraud_check] Checking order {state['order_id']}")
    state["risk_score"] = 0.1
    state["is_flagged"] = state["risk_score"] > 0.7
    return state


def inventory_check(state: OrderState) -> OrderState:
    print(f"[inventory_check] Checking stock for order {state['order_id']}")
    state["out_of_stock_items"] = []
    return state


def negotiate(state: OrderState) -> OrderState:
    print(f"[negotiate] Offering alternative for order {state['order_id']}")
    state["alternative_product_id"] = None
    return state


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

builder.add_edge("negotiate", "await_response")
builder.add_edge("await_response", "finalize")
builder.add_edge("finalize", END)

graph = builder.compile()