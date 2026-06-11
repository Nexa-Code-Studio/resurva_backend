import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DailySummaryResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    summary_date: date
    total_orders: int
    total_revenue: int
    total_discount_given: int
    items_sold: int
    carbon_saved_kg: float
    expiry_alerts_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonthlySummaryResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    year: int
    month: int
    total_orders: int
    total_revenue: int
    total_discount_given: int
    new_customers: int
    carbon_saved_kg: float
    avg_rating: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
