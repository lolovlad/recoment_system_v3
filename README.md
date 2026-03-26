## Рекомендательная система (ЛР1-ЛР4)

Асинхронная рекомендательная система на `FastAPI + Celery + Redis` с двумя ML-сценариями:
- рекомендации товаров по `user_id` (ЛР1, ЛР2, ЛР4);
- оценка времени доставки в минутах (ЛР3, ЛР4).

Проект объединяет:
- `ЛР1` — базовая архитектура (Clean Architecture) и рекомендательный пайплайн;
- `ЛР2` — версионирование данных через `DVC` и хранение в `MinIO`;
- `ЛР3` — модель доставки, экспорт в `ONNX`, инференс через API;
- `ЛР4` — асинхронное выполнение задач через `Celery`.

## Финальная архитектура

- `API` принимает HTTP-запросы и ставит задачи в очередь.
- `Worker` выполняет тяжелые вычисления (рекомендации и доставка).
- `Redis` используется как broker/result backend Celery и как кэш результатов рекомендаций.
- `MinIO` хранит датасеты и артефакты моделей (опционально, при включенной интеграции).

Ключевые пакеты:
- `src/recommender_system/domain` — сущности и интерфейсы;
- `src/recommender_system/application` — бизнес-логика;
- `src/recommender_system/infrastructure` — реализации хранилища и моделей;
- `src/recommender_system/presentation` — `FastAPI`, `Celery`, CLI.

## Быстрый старт

### 1) Требования

- Python `3.11+`
- Poetry
- Docker + Docker Compose

### 2) Установка

```bash
poetry install
```

### 3) Настройка `.env`

Создайте файл из шаблона:

```bash
cp .env.example .env
```

Windows:

```bat
copy .env.example .env
```

Минимально важные переменные:
- `REDIS_URL` — broker/backend Celery;
- `MINIO_*` и `MINIO_MODEL_BUCKET` — если нужны синхронизация и загрузка моделей в MinIO;
- `MODEL_PATH` и `MODEL_REMOTE_PATH` — для сценария модели доставки.

### 4) Запуск (единый раздел)

#### Вариант A: Docker (рекомендуется)

```bash
docker compose up --build -d
```

Поднимутся сервисы: `api`, `worker`, `redis`, `minio`, `minio-init`.

Проверка:
- Swagger: `http://127.0.0.1:8000/docs`
- MinIO Console: `http://localhost:9001`

#### Вариант B: локально без Docker

1. Поднимите Redis (локально или в Docker).
2. Запустите API:

```bash
poetry run uvicorn src.recommender_system.presentation.api:app --reload
```

3. Во втором терминале запустите worker:

```bash
poetry run celery -A recommender_system.presentation.celery_app:celery_app worker --loglevel=info
```

## Главный сценарий проверки системы

Цель: получить `task_id` от `POST` и финальный результат от `GET`.

### Рекомендации

1. Отправить задачу:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/recommendations/generate_for_user" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\": 1}"
```

2. Проверить результат:

```bash
curl "http://127.0.0.1:8000/api/v1/recommendations/results/TASK_ID"
```

### Доставка

1. Отправить задачу:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/delivery/estimate_time" ^
  -H "Content-Type: application/json" ^
  -d "{\"distance\":12.5,\"hour\":18,\"day_of_week\":5,\"items_count\":3}"
```

2. Проверить результат:

```bash
curl "http://127.0.0.1:8000/api/v1/delivery/results/TASK_ID"
```

## API (контракт)

### Рекомендации

| Метод | Путь | Назначение |
|------|------|------------|
| POST | `/api/v1/recommendations/generate_for_user` | Создать задачу генерации рекомендаций по `user_id` |
| GET | `/api/v1/recommendations/results/{task_id}` | Получить статус и список рекомендованных `item_id` |

### Доставка

| Метод | Путь | Назначение |
|------|------|------------|
| POST | `/api/v1/delivery/estimate_time` | Создать задачу оценки времени доставки |
| GET | `/api/v1/delivery/results/{task_id}` | Получить статус и прогноз (минуты) |

## Тесты

Полный прогон:

```bash
poetry run pytest
```

Сценарии ЛР4:

```bat
scripts\lab4_run_tests.bat
```

## Приложение A: данные и DVC (ЛР2)

- Основной датасет рекомендаций: `data/user_history.csv` (`.dvc`-контроль).
- Remote DVC настроен на S3-совместимое хранилище MinIO.
- Локальные секреты DVC держите в `.dvc/config.local` (не коммитится).

Типовой ручной цикл:

```bash
poetry run python scripts/generate_user_history.py --rows 100 --seed 42
dvc add data/user_history.csv
dvc push
```

Полезные bat-скрипты:
- `scripts/setup.bat`
- `scripts/prepare_data.bat`
- `scripts/add_november_data.bat`
- `scripts/switch_to_october.bat`
- `scripts/switch_to_november.bat`

## Приложение B: обучение модели рекомендаций (ЛР1-ЛР2)

```bash
poetry run python scripts/train_recommendation_model.py --data data/user_history.csv --out models/recommendation.onnx --out-meta models/recommendation_meta.json --components 32 --seed 42
```

Также доступно:
- `scripts\train_recommendation_model.bat`
- `scripts\lab4_train_recommendation.bat`

Артефакты:
- `models/recommendation.onnx`
- `models/recommendation_meta.json`

Если артефактов нет локально, worker пытается загрузить их из MinIO; при неуспехе используется `CollaborativeMockModel`.

## Приложение C: обучение модели доставки (ЛР3)

1. Генерация обучающего датасета:

```bash
poetry run python scripts/generate_delivery_data.py --rows 5000 --seed 42 --output data/delivery_train.csv
```

2. Обучение и экспорт ONNX:

```bash
poetry run python scripts/train_delivery_model.py --seed 42 --data data/delivery_train.csv
```

Bat-обертки:
- `scripts\generate_delivery_data.bat`
- `scripts\train_model.bat`

Артефакт по умолчанию: `models/delivery_estimator.onnx`.

## Приложение D: скрипты ЛР4

- `scripts\lab4_prepare_env.bat` — подготовка `.env`
- `scripts\lab4_ensure_data.bat` — проверка/генерация `user_history.csv`
- `scripts\lab4_docker_up.bat` — запуск docker-стека
- `scripts\lab4_verify.py` / `scripts\lab4_verify.ps1` — smoke-проверка API
- `scripts\lab4_quickstart.bat` — полный быстрый сценарий

## Примечания

- `.env` должен лежать в корне репозитория (рядом с `pyproject.toml`).
- В Dockerfile используется `COPY .env`, поэтому создавайте `.env` до `docker compose build`.
- В CI для части тестов используется `CELERY_EAGER_TEST`.
