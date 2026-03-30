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
