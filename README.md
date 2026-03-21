## Проект — ЛР1 + ЛР2 + ЛР3 + ЛР4

Проект демонстрирует:

- **ЛР1**: скелет ИИ‑системы по принципам Clean Architecture (рекомендательная система)
- **ЛР2**: интеграцию хранения и версионирование данных (DVC + MinIO)
- **ЛР3**: ML‑инференс сервис на FastAPI + ONNX Runtime (регрессия: прогноз времени доставки)
- **ЛР4**: асинхронная многокомпонентная система (**Celery + Redis**), вариант 7 — рекомендации по `user_id` через фоновые задачи; доставка — также через Celery (без синхронного ONNX в HTTP)

### Содержание

- Обзор, структура пакета, карта «где что лежит»
- Файл `.env`, таблица переменных, Docker Compose и локальный запуск API/worker
- DVC и `user_history.csv`, CLI, запуск тестов
- ЛР3 — доставка (ONNX, API, curl)
- Рекомендации: обучение ONNX (ЛР1–2)
- ЛР4 — Celery, скрипты `lab4_*`, примеры curl

*Согласованность с репозиторием:* версия Python — `requires-python` в `pyproject.toml`; шаблон переменных — `.env.example`; сервисы и сеть — `docker-compose.yml`.

### Рекомендательная система (контекст варианта 7)

1. **Контекст:** генерация персональных рекомендаций для пользователя (например, **топ‑100** товаров) может быть вычислительно затратной, поэтому выполняется **асинхронно** в worker.
2. **API:**  
   - `POST /api/v1/recommendations/generate_for_user` — JSON с `user_id`, создаётся задача Celery, ответ `{ "task_id": "..." }`.  
   - `GET /api/v1/recommendations/results/{task_id}` — список рекомендованных `item_id` (и статус задачи).
3. **Worker:** получает задачу с `user_id`, **загружает обученную модель** (`TruncatedSVD` по истории из ЛР1–2 или заглушка `CollaborativeMockModel`, если файла модели нет), по матрице взаимодействий формирует **кандидатов** (каталог товаров из обучения), **прогоняет через модель** (латентные факторы), отбирает **топ‑N** (`RECOMMENDATION_TOP_N`, по умолчанию **5**). Список `item_id` дополнительно **сохраняется в Redis** с ключом `recommendations:items:{task_id}` (TTL из `RECOMMENDATION_REDIS_TTL_SECONDS`). Результат той же задачи доступен через Celery result backend для GET API.

> **Важно:** обучение **рекомендательной** модели делается скриптом **`scripts/train_recommendation_model.py`** по данным **`data/user_history.csv`** (ЛР1–2). Это **не** то же самое, что регрессия времени доставки (ЛР3): её обучает **`scripts/train_delivery_model.py`** по `data/delivery_train.csv` → ONNX.

### Структура

- `domain` — сущности и интерфейсы (в том числе `Recommender`, `IDataStorage`)
- `application` — бизнес‑логика (`RecommendationService`, `DataSyncService` и т.п.)
- `infrastructure` — реализации моделей и хранилища (`CollaborativeMockModel`, `TrainedRecommenderModel`, `S3Storage`)
- `presentation` — CLI, FastAPI, Celery (`api.py`, `celery_app.py`, `tasks.py`)
- `env.py` — единая загрузка **`.env`** из корня репозитория (`load_project_env`)
- `scripts` — генерация данных, **`train_recommendation_model.py`** (рекомендации), **`train_delivery_model.py`** (доставка ONNX), MinIO, DVC

### Где worker с моделью и где обучение (карта по репозиторию)

| Что | Где в коде / файлах |
|-----|---------------------|
| **Celery worker** | Запуск: `Dockerfile.worker` или `celery -A recommender_system.presentation.celery_app:celery_app worker`. Задачи: `src/recommender_system/presentation/tasks.py`. |
| **Рекомендации (ЛР4)** | `tasks.py` → `generate_recommendations_for_user` → **`TrainedRecommenderModel`** (ONNX + JSON), если есть **`models/recommendation.onnx`** и **`models/recommendation_meta.json`** (или после синка из MinIO), иначе mock. История: `data/user_history.csv`. Результат — в **Redis** `recommendations:items:{task_id}`. |
| **Обучение рекомендательной модели (ЛР1–2)** | **`scripts/train_recommendation_model.py`** → **`recommendation.onnx`** (скоринг SVD) + **`recommendation_meta.json`**, загрузка в MinIO при `MINIO_*`. |
| **Доставка ONNX (ЛР3) в worker** | `tasks.py` → `estimate_delivery_task` → `_get_inference_service_singleton()`: `MODEL_PATH`, MinIO (`MINIO_*`, `MODEL_REMOTE_PATH`). |
| **Обучение модели доставки (ЛР3)** | **`scripts/train_delivery_model.py`** (bat: **`scripts/train_model.bat`** — то же самое). Перед этим — **`scripts/generate_delivery_data.py`**. Артефакт: `models/delivery_estimator.onnx`, опционально upload в MinIO. |
| **Redis / Celery** | **`REDIS_URL`** в `.env`; `celery_app.py` через `load_project_env()`. |

### Файл `.env` в корне проекта

1. Скопируйте шаблон: **`cp .env.example .env`** (Windows: `copy .env.example .env`).
2. Подставьте значения. Файл **`.env` в Git не коммитится** (см. `.gitignore`).
3. Загрузка выполняется функцией **`load_project_env()`** из `src/recommender_system/env.py` (обёртка над `python-dotenv`): читается **только** `.env` в корне репозитория (рядом с `pyproject.toml`). Уже заданные в ОС или в Docker переменные **не перезаписываются** (`override=False`).

Где вызывается `load_project_env`:

- при импорте **`celery_app`** (API, worker, Celery);
- **`dependencies.get_inference_service`**, **`tasks._get_inference_service_singleton`**;
- **`cli`** при старте;
- скрипты **`train_recommendation_model.py`**, **`train_delivery_model.py`**, **`init_data.py`**.

Переменные (полный шаблон — **`.env.example`**; в коде пути к ONNX рекомендаций **не** задаются через env: файлы `models/recommendation.onnx` и `models/recommendation_meta.json`, см. `recommendation_artifacts.py`):

| Переменная | Назначение |
|------------|------------|
| `REDIS_URL` | Celery broker и result backend, например `redis://127.0.0.1:6379/0` локально |
| `RECOMMENDATION_TOP_N` | Топ рекомендаций; если не задано, в коде по умолчанию **5** |
| `RECOMMENDATION_REDIS_TTL_SECONDS` | TTL ключа в Redis с результатом (`recommendations:items:{task_id}`) |
| `MODEL_PATH` | Путь к ONNX модели **доставки** (ЛР3) |
| `MODEL_REMOTE_PATH` | Ключ объекта доставки в бакете `MINIO_MODEL_BUCKET` |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Доступ к MinIO |
| `MINIO_BUCKET` | Бакет для датасетов (ЛР2, DVC и т.п.) |
| `MINIO_MODEL_BUCKET` | Бакет для моделей (`delivery_estimator.onnx`, артефакты рекомендаций) |
| `CELERY_EAGER_TEST` | Только для pytest (см. `tests/conftest.py`) |

**Docker Compose:** в образах API и worker — **`COPY .env`** (перед **`docker compose build`** создайте `.env`, например **`copy .env.example .env`**). У сервисов **`api`** и **`worker`** подключён опциональный **`env_file: .env`**; блок **`environment`** задаёт **`REDIS_URL`**, **`MINIO_*`** для сети контейнеров и **имеет приоритет** над значениями из файла `.env` (как у `load_dotenv` с `override=False`). Переменные вроде **`RECOMMENDATION_TOP_N`** без дубликата в `environment` подхватываются из `.env` в контейнере.

### Требования

- Установлен Docker и Docker Compose
- **Python 3.11+** (как в `pyproject.toml`, поле `requires-python`)
- Poetry (для установки зависимостей)

### Настройка окружения

1. Установить зависимости:

```bash
poetry install
```

2. Создать `.env` из шаблона и при необходимости отредактировать:

```bash
cp .env.example .env
```

Содержимое и комментарии — в **`.env.example`**. Минимум для локального API+worker: **`REDIS_URL`**, при работе с MinIO — блок **`MINIO_*`** и при необходимости **`MODEL_PATH`**.

> Для DVC доступ к MinIO на стенде настроен через `.dvc/config.local`, который **не попадает в Git**.

### Запуск инфраструктуры (Docker Compose)

```bash
docker compose up --build -d
```

Будут подняты:

- **`redis`** — брокер и backend Celery (порт **6379**)
- **`api`** — FastAPI на порту **8000** (`REDIS_URL=redis://redis:6379/0`)
- **`worker`** — Celery worker; те же **`environment`** и **`env_file`** (опционально), что у **`api`**
- **`minio`** — S3‑совместимое хранилище (порты `9000` — API, `9001` — Console)
- **`minio-init`** — создаёт бакеты `datasets` и `models`

Консоль MinIO: `http://localhost:9001` (логин/пароль по умолчанию: `minioadmin` / `minioadmin`).

**Локальный запуск API и worker без Docker** (нужен Redis; в **`.env`**: `REDIS_URL=redis://127.0.0.1:6379/0`):

```bash
poetry run uvicorn src.recommender_system.presentation.api:app --reload
```

Во втором терминале из корня репозитория:

```bash
poetry run celery -A recommender_system.presentation.celery_app:celery_app worker --loglevel=info
```

Переменные подхватятся при импорте `celery_app`. На Linux/macOS при желании: `export $(grep -v '^#' .env | xargs)` перед командами.

Ту же команду **`uvicorn`** можно использовать в сценариях раздела **«ЛР3»** (п. «2) Запуск API») — повторять блок с командой там не обязательно.

### Настройка DVC и remote

В репозитории уже инициализирован DVC и настроен remote `myremote`:

```ini
[core]
    remote = myremote
['remote "myremote"']
    url = s3://datasets
    endpointurl = http://localhost:9000
```

Параметры авторизации к MinIO вынесены в локальный конфиг DVC (не попадает в Git):

```ini
; файл .dvc/config.local (создаётся локально)
['remote "myremote"']
    access_key_id = minioadmin
    secret_access_key = minioadmin
```

При необходимости можно изменить ключи на свои, либо настроить переменные окружения для DVC.

### Работа с данными и версиями (user_history.csv)

Датасет истории взаимодействий хранится в `data/user_history.csv` и находится под версионным контролем DVC (`data/user_history.csv.dvc`).  
В папке `scripts` есть набор скриптов для подготовки и переключения версий данных:

- `setup.bat` — полная автоматическая настройка (запуск MinIO, инициализация DVC, генерация `user_history.csv`, добавление в DVC, пуш в MinIO — версия v1.0, октябрь)
- `prepare_data.bat` — добавить текущую версию `user_history.csv` в DVC и отправить в MinIO
- `add_november_data.bat` — добавить данные за ноябрь и сформировать версию v2.0 (октябрь + ноябрь)
- `switch_to_october.bat` — переключиться на версию v1.0 (только октябрь)
- `switch_to_november.bat` — переключиться на версию v2.0 (октябрь + ноябрь)
- `demo.bat` — демонстрация работы системы (проверка MinIO, DVC и скрипта инициализации данных)

Ручная последовательность (если не использовать `.bat`):

```bash
# генерация истории взаимодействий
poetry run python scripts/generate_user_history.py --rows 100 --seed 42

# добавить в DVC и отправить в MinIO
dvc add data/user_history.csv
dvc push
```

### Инициализация данных (DataSyncService)

Слой `infrastructure` содержит класс `S3Storage`, реализующий интерфейс `IDataStorage` и инкапсулирующий работу с `boto3` и S3‑совместимым API MinIO.  
Слой `application` содержит `DataSyncService`, который при запуске проверяет наличие локального файла и, если его нет, скачивает актуальные данные из хранилища.

Это позволяет одной командой DVC (`dvc pull` или соответствующий скрипт) подтянуть нужный "срез" данных (например, v1.0 или v2.0), после чего `DataSyncService` гарантирует наличие локального `user_history.csv` для работы рекомендательной модели.

### Запуск CLI

После настройки зависимостей и данных:

```bash
poetry run python -m src.recommender_system.presentation.cli --user-id u1 --items itemA,itemB
```

### Запуск тестов

```bash
poetry run pytest
```

Покрытие: домен и application, часть инфраструктуры (ONNX, моки), FastAPI-эндпоинты и Celery в режиме **`CELERY_EAGER_TEST`** (без обязательного живого Redis в CI).

---

## ЛР3 — Delivery Time Estimator (FastAPI + ONNX Runtime)

### 1) Обучение и экспорт модели в ONNX

Скрипт обучения **генерирует синтетический датасет**, обучает `GradientBoostingRegressor` и сохраняет модель в:

- `models/delivery_estimator.onnx`

Дополнительно (для ЛР3): после обучения модель **автоматически загружается в MinIO** в бакет `models`, если заданы переменные окружения MinIO.

Важно: генерация датасета и обучение разделены. Сначала создайте `data/delivery_train.csv`, затем обучайте.

Запуск:

```bash
poetry run python scripts/generate_delivery_data.py --rows 5000 --seed 42 --output data/delivery_train.csv
poetry run python scripts/train_delivery_model.py --seed 42 --data data/delivery_train.csv
```

Или через bat:

```bash
scripts\generate_delivery_data.bat
scripts\train_model.bat
```

```bash
dvc add data/delivery_train.csv
dvc push
```

### 2) Запуск API

Команда совпадает с блоком **«Локальный запуск API и worker без Docker»** выше (раздел «Запуск инфраструктуры (Docker Compose)»):

```bash
poetry run uvicorn src.recommender_system.presentation.api:app --reload
```

Или: `scripts\run_api.bat`

Эндпоинты (асинхронно, ЛР4):

- `POST /api/v1/delivery/estimate_time` → **202** + `task_id`
- `GET /api/v1/delivery/results/{task_id}` → `status`, `result` (минуты)

### 3) Пример запроса (curl)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/delivery/estimate_time" ^
  -H "Content-Type: application/json" ^
  -d "{\"distance\":12.5,\"hour\":18,\"day_of_week\":5,\"items_count\":3}"
```

Ответ (202):

```json
{"task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}
```

Результат:

```bash
curl "http://127.0.0.1:8000/api/v1/delivery/results/TASK_ID"
```

### 4) Smoke-test (PowerShell)

```powershell
.\scripts\smoke_test_api.ps1
```

### 5) Переменные окружения (опционально)

По умолчанию API ищет модель в `models/delivery_estimator.onnx`. Можно переопределить:

- `MODEL_PATH` — путь к локальному ONNX файлу
- `MODEL_REMOTE_PATH` — имя/путь объекта в бакете (для S3/MinIO)

Если нужно показать полный сценарий ЛР3 **(обучили → загрузили в MinIO → API скачал и использовал)**:

1) Поднимите MinIO:

```bash
docker compose up -d
```

В `docker-compose.yml` автоматически создаются бакеты:
- `datasets` (ЛР2)
- `models` (ЛР3)

2) Создайте `.env` и укажите MinIO:

```env
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=datasets
MINIO_MODEL_BUCKET=models
```

3) Обучите модель — скрипт сам зальёт `models/delivery_estimator.onnx` в MinIO (`s3://models/delivery_estimator.onnx`):

```bash
scripts\train_model.bat
```

4) Удалите локальный файл модели (чтобы убедиться, что API скачивает из MinIO):

```bash
del models\delivery_estimator.onnx
```

5) Запустите API — при первом обращении DI скачает модель из MinIO и использует её:

```bash
scripts\run_api.bat
```

---

## Рекомендации: обучение модели (ЛР1–2) — ONNX + JSON

После того как в `data/user_history.csv` есть история взаимодействий:

```bash
poetry run python scripts/train_recommendation_model.py --data data/user_history.csv --out models/recommendation.onnx --out-meta models/recommendation_meta.json --components 32 --seed 42
```

Или: `scripts\train_recommendation_model.bat` (те же пути по умолчанию).

В **Docker Compose** каталог **`./models`** монтируется в **`/app/models`**, **`./data`** — в **`/app/data`** (read-only), чтобы worker видел **`data/user_history.csv`** для последних взаимодействий пользователя; при отсутствии файлов моделей worker пытается **синхронизацию из MinIO** (`recommendation_model_sync`, бакет `models`, ключи `recommendation.onnx` / `recommendation_meta.json`). Если скачать нельзя — используется **`CollaborativeMockModel`**.

---

## ЛР4 — Celery + Redis + Docker (вариант 7: рекомендации)

### Архитектура

- HTTP **не** выполняет тяжёлую логику рекомендаций и ONNX — только ставит задачи Celery и отдаёт `task_id`.
- **Worker** выполняет задачи: загрузка/кеш **модели рекомендаций** через синглтоны (`lru_cache`), инференс (кандидаты → скоры → **топ‑N** `item_id`), запись списка в **Redis** (`recommendations:items:{task_id}`) и возврат результата в Celery backend для GET.
- **Redis** — broker, result backend Celery и (опционально) кэш списка рекомендаций; URL в **`.env`**: **`REDIS_URL`**.

Файлы: `src/recommender_system/presentation/celery_app.py`, `tasks.py`, `api.py`.

### API (контракт ЛР4)

| Метод | Путь | Описание |
|--------|------|----------|
| POST | `/api/v1/recommendations/generate_for_user` | Тело: `{"user_id": int}`. Ответ **202**: `{"task_id": "..."}` |
| GET | `/api/v1/recommendations/results/{task_id}` | `task_id`, `status` ∈ `PENDING \| STARTED \| SUCCESS \| FAILURE`, `result`: список `item_id` или `null` |

Доставка (ЛР3+4, асинхронно):

| POST | `/api/v1/delivery/estimate_time` | **202** + `task_id` |
| GET | `/api/v1/delivery/results/{task_id}` | При `SUCCESS` в JSON поле **`result`** — прогноз в минутах (`float`) |

### Пошаговый гайд: запуск и проверка ЛР4

**Цель:** поднять Redis + API + Celery worker, иметь данные и ONNX рекомендаций, убедиться, что `POST` возвращает `task_id`, а `GET` — `SUCCESS` и список `item_id`.

| Шаг | Действие | Команда / скрипт |
|-----|----------|------------------|
| **0** | Установить зависимости | `poetry install` |
| **1** | Создать `.env` из шаблона (если ещё нет) | `scripts\lab4_prepare_env.bat` или `cp .env.example .env` |
| **2** | Убедиться в данных `user_history.csv` | `scripts\lab4_ensure_data.bat` (при отсутствии файла сгенерирует 200 строк) или `dvc pull` / свой CSV |
| **3** | Обучить рекомендации → `models/recommendation.onnx` + `recommendation_meta.json` | `scripts\lab4_train_recommendation.bat` или `scripts\train_recommendation_model.bat` |
| **4** | Запустить стек в Docker (redis, api, worker, minio) | `scripts\lab4_docker_up.bat` или `docker compose up --build -d` |
| **5** | Подождать ~10–20 с, пока контейнеры станут healthy | — |
| **6** | **Автопроверка API** (OpenAPI → POST → опрос GET до `SUCCESS`) | `poetry run python scripts/lab4_verify.py` или `powershell -File scripts\lab4_verify.ps1` |
| **7** | Ручная проверка в браузере | `http://127.0.0.1:8000/docs` — вызвать эндпоинты рекомендаций |
| **8** | Опционально: Redis CLI — ключ с результатом | `docker exec -it redis_recommender_system_v3 redis-cli GET "recommendations:items:<TASK_ID>"` (после успешной задачи; значение — JSON массив `item_id`) |

**Один сценарий «всё подряд» (Windows):** после `poetry install` выполните:

```bat
scripts\lab4_quickstart.bat
```

Скрипт: подготовка `.env` → данные → обучение → `docker compose up --build -d` → пауза 15 с → `lab4_verify.py`.

> **Без Docker (только локально):** поднимите Redis (`docker compose up -d redis` или свой инстанс), в двух терминалах из корня с `REDIS_URL` в `.env`: `poetry run uvicorn ...` и `poetry run celery -A recommender_system.presentation.celery_app:celery_app worker --loglevel=info` (см. раздел «Запуск инфраструктуры» выше в README).

### Автоматические скрипты (`scripts/`)

| Скрипт | Назначение |
|--------|------------|
| `lab4_prepare_env.bat` | Копирует `.env.example` → `.env`, если `.env` нет |
| `lab4_ensure_data.bat` | Проверяет `data/user_history.csv`; при отсутствии вызывает `generate_user_history.py` |
| `lab4_train_recommendation.bat` | Обёртка над `train_recommendation_model.bat` (ONNX + meta + MinIO) |
| `lab4_docker_up.bat` | `docker compose up --build -d` |
| `lab4_verify.py` | Python: проверка `/openapi.json`, POST рекомендаций, опрос GET до `SUCCESS` (аргументы: `[URL] [user_id]`) |
| `lab4_verify.ps1` | То же в PowerShell (`-BaseUrl`, `-UserId`, `-TimeoutSec`) |
| `lab4_run_tests.bat` | Pytest только сценарии ЛР4 + обучение рекомендаций |
| `lab4_quickstart.bat` | Полная цепочка: env → данные → обучение → Docker → verify |

### Docker (образы)

- **`Dockerfile`** — API (Uvicorn).
- **`Dockerfile.worker`** — `celery -A recommender_system.presentation.celery_app:celery_app worker --loglevel=info`.
- Сборка **без лишнего**: в образ не попадают **README**, **scripts**, **tests**, каталоги **data/models** из контекста (см. **`.dockerignore`**); зависимости — **`poetry install --without dev`** (без pytest и др. из dev-группы), пакет подхватывается через **`PYTHONPATH=/app/src`**.
- **`COPY .env`** в обоих Dockerfile — перед сборкой создайте **`.env`** в корне (например **`copy .env.example .env`**), иначе шаг **`COPY`** завершится ошибкой.
- В **`docker-compose.yml`** у **`api`** и **`worker`** заданы **`env_file: .env`** (опционально) и **`environment`** для Redis/MinIO; каталог **`./models`** монтируется в **`/app/models`** (в образ **models** не копируется).

Swagger: `http://127.0.0.1:8000/docs`.

### Примеры curl (рекомендации)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/recommendations/generate_for_user" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\": 1}"
```

Ответ **202**: `{"task_id": "..."}`. Затем:

```bash
curl "http://127.0.0.1:8000/api/v1/recommendations/results/TASK_ID"
```

Пример при `SUCCESS`: `"status":"SUCCESS"`, `"result":[...]`.

### Пример curl (доставка, асинхронно)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/delivery/estimate_time" ^
  -H "Content-Type: application/json" ^
  -d "{\"distance\":12.5,\"hour\":18,\"day_of_week\":5,\"items_count\":3}"
curl "http://127.0.0.1:8000/api/v1/delivery/results/TASK_ID"
```

### Переменные окружения (ЛР4)

| Переменная | Назначение |
|------------|------------|
| `REDIS_URL` | Broker и backend Celery; в Docker переопределяется в `docker-compose.yml` |
| `RECOMMENDATION_TOP_N`, `RECOMMENDATION_REDIS_TTL_SECONDS` | Топ-N рекомендаций, TTL ключа в Redis (пути к ONNX/мете зафиксированы в коде) |

Шаблон — **`.env.example`**. Список `item_id` дублируется в Redis (`recommendations:items:{task_id}`).

### Тестирование (pytest и скрипты)

**1. Автотесты проекта (в т.ч. ЛР4, без реального Redis в CI):**

```bash
poetry run pytest
```

**2. Только ЛР4 + обучение рекомендаций:**

```bash
scripts\lab4_run_tests.bat
```

или:

```bash
poetry run pytest tests/test_lab4_recommendations_api.py tests/test_lab4_worker.py tests/test_lab4_integration.py tests/test_train_recommendation_model.py -v
```

**3. Реальный Redis (опционально):** снимите `CELERY_EAGER_TEST`, задайте `REDIS_URL`, поднимите Redis, затем `pytest` как в п.2.

**4. Доставка (smoke, другой сценарий):**

```powershell
.\scripts\smoke_test_api.ps1
```
