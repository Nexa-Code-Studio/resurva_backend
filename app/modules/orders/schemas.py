import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import OrderChannel, OrderStatus


class OrderItemBase(BaseModel):
    product_id: uuid.UUID
    quantity: int


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: uuid.UUID
    unit_price: int
    subtotal: int
    product_name: str | None = None
    options: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    store_id: uuid.UUID
    channel: OrderChannel = OrderChannel.MARKETPLACE


class OrderCreate(OrderBase):
    items: list[OrderItemCreate]
    notes: str | None = None


class OrderUpdateStatus(BaseModel):
    status: OrderStatus


class OrderResponse(OrderBase):
    id: uuid.UUID
    user_id: uuid.UUID
    total_price: int
    total_discount: int
    final_price: int
    status: OrderStatus
    created_at: datetime
    order_items: list[OrderItemResponse]
    customer_name: str | None = None
    payment_method: str | None = None
    order_type: str | None = None
    notes: str | None = None
    daily_code: str | None = None

    model_config = ConfigDict(from_attributes=True)
