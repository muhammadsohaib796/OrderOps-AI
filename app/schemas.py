from pydantic import BaseModel
from typing import List
from typing import Optional


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItemCreate]


class CustomerCreate(BaseModel):
    name: str
    email: str
    phone: str | None = None


class DemoOrderCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    product_id: Optional[int] = None