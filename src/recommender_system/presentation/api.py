"""
FastAPI: ЛР3 (доставка) + ЛР4 (асинхронные рекомендации через Celery).

Синхронный вызов ONNX в HTTP убран — прогноз доставки выполняется через Celery-задачу.

Переменные окружения подгружаются из `.env` при импорте `celery_app` (см. `env.load_project_env`).
"""
from __future__ import annotations

import uuid

from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException, status

from ..domain.entities import (
    DeliveryRequest,
    DeliveryTaskResultResponse,
    RecommendationGenerateRequest,
    RecommendationTaskResultResponse,
    TaskCreatedResponse,
)
from .celery_app import celery_app
from .tasks import estimate_delivery_task, generate_recommendations_for_user


def _map_celery_state_to_api(state: str) -> str:
    """Приводит состояние Celery к контракту API: PENDING | STARTED | SUCCESS | FAILURE."""
    if state in ("PENDING",):
        return "PENDING"
    if state in ("STARTED", "RETRY"):
        return "STARTED"
    if state in ("SUCCESS",):
        return "SUCCESS"
    if state in ("FAILURE", "REVOKED"):
        return "FAILURE"
    return "PENDING"


app = FastAPI(
    title="Recommender System API",
    version="2.0.0",
    description="ЛР3: доставка (async). ЛР4: рекомендации (Celery + Redis).",
)


@app.post(
    "/api/v1/recommendations/generate_for_user",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def post_generate_recommendations(request: RecommendationGenerateRequest) -> TaskCreatedResponse:
    """Ставит задачу генерации рекомендаций; логика выполняется в worker."""
    async_result = generate_recommendations_for_user.delay(request.user_id)
    return TaskCreatedResponse(task_id=async_result.id)


@app.get(
    "/api/v1/recommendations/results/{task_id}",
    response_model=RecommendationTaskResultResponse,
)
def get_recommendation_results(task_id: str) -> RecommendationTaskResultResponse:
    """Возвращает статус и результат (список item_id) по task_id."""
    try:
        uuid.UUID(task_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task_id",
        ) from e

    result = AsyncResult(task_id, app=celery_app)
    api_status = _map_celery_state_to_api(result.state)

    if result.state == "FAILURE":
        err = str(result.result) if result.result is not None else "Task failed"
        return RecommendationTaskResultResponse(
            task_id=task_id,
            status=api_status,
            result=None,
            error=err,
        )

    if result.successful():
        payload = result.result
        if not isinstance(payload, list):
            payload = list(payload) if payload is not None else []
        return RecommendationTaskResultResponse(
            task_id=task_id,
            status=api_status,
            result=[int(x) for x in payload],
            error=None,
        )

    return RecommendationTaskResultResponse(
        task_id=task_id,
        status=api_status,
        result=None,
        error=None,
    )


@app.post(
    "/api/v1/delivery/estimate_time",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def post_estimate_delivery(request: DeliveryRequest) -> TaskCreatedResponse:
    """Асинхронный прогноз времени доставки (ONNX в worker)."""
    payload = request.model_dump()
    async_result = estimate_delivery_task.delay(payload)
    return TaskCreatedResponse(task_id=async_result.id)


@app.get(
    "/api/v1/delivery/results/{task_id}",
    response_model=DeliveryTaskResultResponse,
)
def get_delivery_results(task_id: str) -> DeliveryTaskResultResponse:
    """Статус и результат (estimated_minutes) по task_id."""
    try:
        uuid.UUID(task_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task_id",
        ) from e

    result = AsyncResult(task_id, app=celery_app)
    api_status = _map_celery_state_to_api(result.state)

    if result.state == "FAILURE":
        err = str(result.result) if result.result is not None else "Task failed"
        return DeliveryTaskResultResponse(task_id=task_id, status=api_status, result=None, error=err)

    if result.successful():
        val = result.result
        minutes = float(val) if val is not None else None
        return DeliveryTaskResultResponse(task_id=task_id, status=api_status, result=minutes, error=None)

    return DeliveryTaskResultResponse(task_id=task_id, status=api_status, result=None, error=None)

