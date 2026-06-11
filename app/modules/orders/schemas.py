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

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    store_id: uuid.UUID
    channel: OrderChannel = OrderChannel.MARKETPLACE


class OrderCreate(OrderBase):
    items: list[OrderItemCreate]


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

    model_config = ConfigDict(from_attributes=True)
