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


# --- Lab 4: async recommendations API (Celery) ---


class RecommendationGenerateRequest(BaseModel):
    """Тело запроса POST /api/v1/recommendations/generate_for_user."""

    user_id: int = Field(..., ge=1)


class TaskCreatedResponse(BaseModel):
    """Ответ после постановки Celery-задачи."""

    task_id: str


class RecommendationTaskResultResponse(BaseModel):
    """Результат GET /api/v1/recommendations/results/{task_id}."""

    task_id: str
    status: str  # PENDING | STARTED | SUCCESS | FAILURE
    result: list[int] | None = None
    error: str | None = None


class DeliveryTaskResultResponse(BaseModel):
    """Результат GET /api/v1/delivery/results/{task_id} (асинхронная доставка, ЛР3+4)."""

    task_id: str
    status: str
    result: float | None = None
    error: str | None = None
