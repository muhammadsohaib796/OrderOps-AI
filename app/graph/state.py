from typing import TypedDict, Optional


class OrderState(TypedDict):
    order_id: int
    customer_id: int
    risk_score: Optional[float]
    is_flagged: bool
    out_of_stock_items: list[int]
    alternative_products: dict[int, Optional[int]]
    customer_response: Optional[str]
    final_status: Optional[str]