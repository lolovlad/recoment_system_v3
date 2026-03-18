from pydantic import BaseModel, Field


class UserHistory(BaseModel):
    user_id: str
    last_items: list[str]


class Recommendation(BaseModel):
    suggested_items: list[str]
    engine_version: str


class DeliveryRequest(BaseModel):
    distance: float = Field(..., ge=0)
    hour: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)
    items_count: int = Field(..., ge=1)


class DeliveryResponse(BaseModel):
    estimated_minutes: float
