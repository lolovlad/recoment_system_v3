# API (FastAPI). В образе: src + runtime-зависимости (без dev, без scripts/tests/README).
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* ./

RUN poetry install --without dev --no-interaction --no-root

COPY .env ./.env

COPY src ./src

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "recommender_system.presentation.api:app", "--host", "0.0.0.0", "--port", "8000"]
