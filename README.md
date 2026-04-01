## Рекомендательная система (ЛР1-ЛР4)

Асинхронный сервис рекомендаций на `FastAPI + Celery + Redis`.
API ставит задачу в очередь, worker вычисляет рекомендации и результат читается по `task_id`.

## Финальная архитектура

- `api` — HTTP-контракт и постановка задач.
- `worker` — генерация рекомендаций по `user_id`.
- `redis` — Celery broker и result backend.
- `minio` — хранилище датасетов/артефактов (опционально).

Ключевые пакеты:
- `src/recommender_system/domain`
- `src/recommender_system/application`
- `src/recommender_system/infrastructure`
- `src/recommender_system/presentation`

## Установка и настройка

### Требования

- Python `3.11+`
- Poetry
- Docker + Docker Compose

### Установка зависимостей

```bash
poetry install
```

### `.env`

Создайте и заполните `.env` в корне проекта.

Минимально:
- `REDIS_URL=redis://127.0.0.1:6379/0`
- `RECOMMENDATION_TOP_N=5` (опционально)
- `MINIO_*` и `MINIO_MODEL_BUCKET` (только если используете MinIO)

### Настройка DVC (обязательно для данных)

Проект использует DVC для версионирования `data/user_history.csv`.

Проверьте, что remote настроен на MinIO:

```ini
[core]
    remote = myremote
['remote "myremote"']
    url = s3://datasets
    endpointurl = http://localhost:9000
```

Локальные секреты храните в `.dvc/config.local` (файл не коммитится):

```ini
['remote "myremote"']
    access_key_id = <your_access_key>
    secret_access_key = <your_secret_key>
```

Базовые команды:

```bash
# подтянуть актуальную версию данных
dvc pull

# после обновления локальных данных — зафиксировать и отправить
dvc add data/user_history.csv
dvc push
```

## Способы запуска

### Docker (рекомендуется)

```bash
docker compose up --build -d
```

Проверка:
- Swagger: `http://127.0.0.1:8000/docs`
- MinIO Console: `http://localhost:9001`

### Локально без Docker

1. Поднимите Redis.
2. Запустите API:

```bash
poetry run uvicorn src.recommender_system.presentation.api:app --reload
```

3. Во втором терминале запустите worker:

```bash
poetry run celery -A recommender_system.presentation.celery_app:celery_app worker --loglevel=info
```

## Главный сценарий проверки

1. Создать задачу рекомендаций:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/recommendations/generate_for_user" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\": 1}"
```

2. Получить результат:

```bash
curl "http://127.0.0.1:8000/api/v1/recommendations/results/TASK_ID"
```

## API

| Метод | Путь | Назначение |
|------|------|------------|
| POST | `/api/v1/recommendations/generate_for_user` | Создать асинхронную задачу |
| GET | `/api/v1/recommendations/results/{task_id}` | Получить статус и список `item_id` |

## Данные и обучение модели

- Датасет рекомендаций: `data/user_history.csv` (под DVC).
- Обучение:

```bash
poetry run python scripts/train_recommendation_model.py --data data/user_history.csv --out models/recommendation.onnx --out-meta models/recommendation_meta.json --components 32 --seed 42
```

- Bat-скрипты:
  - `scripts\train_recommendation_model.bat`
  - `scripts\lab4_train_recommendation.bat`

Если локальных артефактов нет, worker пытается скачать их из MinIO; при неуспехе использует `CollaborativeMockModel`.

## Тестирование

```bash
poetry run pytest
```

---

## ЛР5 (вариант 7): CI/CD + MLflow (Postgres + MinIO) + self-hosted runner

ЛР5 встроена в текущую инфраструктуру проекта:
- MLflow + Postgres добавлены как сервисы в **текущий** `docker-compose.yml`;
- MinIO используется тот же, что и для DVC/моделей (добавлен bucket `mlflow`);
- ML логирование добавлено в существующий скрипт `scripts/train_recommendation_model.py`;
- CI/CD workflow собирает и деплоит **api/worker** (существующие Dockerfile’ы) через `docker compose`.

### Развертывание MLflow (Docker Compose)

Поднимите стек:

```bash
docker compose up --build -d
```

Проверка:
- MLflow UI: `http://localhost:5000`
- MinIO Console: `http://localhost:9001`

Bucket `mlflow` создается автоматически сервисом `minio-init`.

### Логирование обучения в MLflow

Скрипт: `scripts/train_recommendation_model.py`

Если задан `MLFLOW_TRACKING_URI`, скрипт логирует артефакты обучения в MLflow:
- параметры (components/seed/data_path)
- артефакты `recommendation.onnx` и `recommendation_meta.json` в MLflow (через MinIO)

Пример:

```bash
set MLFLOW_TRACKING_URI=http://localhost:5000
poetry run python scripts/train_recommendation_model.py --data data/user_history.csv
```


### CI/CD (self-hosted runner)

Workflow: `.github/workflows/main.yml`

Secrets:
- `DOCKER_USERNAME`, `DOCKER_PASSWORD` — если пушите в Docker Hub (иначе используется GHCR)
- `MLFLOW_TRACKING_URI` — URL MLflow, доступный с self-hosted runner
- `DVC_ACCESS_KEY_ID`, `DVC_SECRET_ACCESS_KEY` — доступ к DVC remote (MinIO/S3)
- `DVC_ENDPOINTURL` — endpoint для DVC remote (например `http://localhost:9000`)

При push в `master`:
- **test**: `poetry install` → `ruff check` → `pytest`
- **train**: настройка DVC remote secrets → `dvc pull` → обучение новой модели `scripts/train_recommendation_model.py` с логированием в MLflow
- **build**: локальная сборка Docker-образов `recsys-api:latest` и `recsys-worker:latest`

