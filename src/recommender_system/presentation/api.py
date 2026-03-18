from __future__ import annotations

import numpy as np
from fastapi import Depends, FastAPI

from ..application.services import InferenceService
from ..domain.entities import DeliveryRequest, DeliveryResponse
from .dependencies import get_inference_service


app = FastAPI(title="Delivery Time Estimator", version="1.0.0")


@app.post("/api/v1/delivery/estimate_time", response_model=DeliveryResponse)
def estimate_time(
    request: DeliveryRequest,
    service: InferenceService = Depends(get_inference_service),
) -> DeliveryResponse:
    x = np.array([[request.distance, request.hour, request.day_of_week, request.items_count]], dtype=np.float32)
    minutes = service.predict(x)
    return DeliveryResponse(estimated_minutes=minutes)

