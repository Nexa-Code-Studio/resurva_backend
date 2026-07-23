import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.modules.reviews.schemas import ReviewResponse
from app.core.enums import OrderChannel, OrderStatus, PaymentMethod


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
    payment_method: PaymentMethod | None = None
    payment_details: dict | None = None
    status: OrderStatus | None = None
    discount_id: uuid.UUID | None = None



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
    store_name: str | None = None
    store_address: str | None = None
    store_image_url: str | None = None
    store_latitude: float | None = None
    store_longitude: float | None = None
    payment_method: str | None = None
    order_type: str | None = None
    notes: str | None = None
    daily_code: str | None = None
    review: Optional["ReviewResponse"] = None
    applied_voucher_code: str | None = None
    applied_voucher_name: str | None = None
    voucher_discount: int = 0

    model_config = ConfigDict(from_attributes=True)
