import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import DiscountType


class DiscountCreate(BaseModel):
    store_id: uuid.UUID
    name: str
    type: DiscountType
    value: int
    max_discount: int | None = None
    min_purchase: int = 0
    start_time: datetime
    end_time: datetime
    quota: int | None = None
    per_user_limit: int = 1
    is_voucher: bool = False
    code: str | None = None


class DiscountResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    type: DiscountType
    value: int
    max_discount: int | None
    min_purchase: int
    start_time: datetime
    end_time: datetime
    quota: int | None
    per_user_limit: int
    is_voucher: bool
    code: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
