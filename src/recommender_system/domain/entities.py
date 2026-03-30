from pydantic import BaseModel, Field


class UserHistory(BaseModel):
    user_id: str
    last_items: list[str]


class Recommendation(BaseModel):
    suggested_items: list[str]
    engine_version: str


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
