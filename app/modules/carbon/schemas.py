import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CarbonLogResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    user_id: uuid.UUID
    carbon_saved_kg: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
