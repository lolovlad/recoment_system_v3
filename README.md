## Проект — ЛР1 + ЛР2 + ЛР3

Проект демонстрирует:

- **ЛР1**: скелет ИИ‑системы по принципам Clean Architecture (рекомендательная система)
- **ЛР2**: интеграцию хранения и версионирование данных (DVC + MinIO)
- **ЛР3**: ML‑инференс сервис на FastAPI + ONNX Runtime (регрессия: прогноз времени доставки)

### Структура

- `domain` — сущности и интерфейсы (в том числе `Recommender`, `IDataStorage`)
- `application` — бизнес‑логика (`RecommendationService`, `DataSyncService` и т.п.)
- `infrastructure` — реализации моделей и хранилища (`CollaborativeMockModel`, `S3Storage`)
- `presentation` — CLI‑интерфейс
- `scripts` — скрипты для настройки MinIO, DVC и демонстрации версий данных

### Требования

- Установлен Docker и Docker Compose
- Python 3.10+
- Poetry (для установки зависимостей)

### Настройка окружения

1. Установить зависимости:

```bash
poetry install
```

2. (Опционально) создать файл `.env` в корне и прописать в нём параметры подключения к MinIO (если хотите использовать их в коде):

```env
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=datasets
MINIO_MODEL_BUCKET=models
```

> Для DVC доступ к MinIO на стенде настроен через `.dvc/config.local`, который **не попадает в Git**.

### Запуск MinIO (Docker Compose)

```bash
docker compose up -d
```

Будут подняты:

- сервис `minio` (S3‑совместимое хранилище, порты `9000` — API, `9001` — Console)
- сервис `minio-init`, который автоматически создаёт бакет `datasets` и `models`

Консоль MinIO будет доступна по адресу `http://localhost:9001` (логин/пароль по умолчанию: `minioadmin` / `minioadmin`).

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

Тесты проверяют бизнес‑логику слоя Application и не зависят от конкретных реализаций инфраструктуры.

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
poetry run python scripts/train_model.py --seed 42 --data data/delivery_train.csv
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

Команда:

```bash
poetry run uvicorn src.recommender_system.presentation.api:app --reload
```

Или через bat:

```bash
scripts\run_api.bat
```

Эндпоинт:

- `POST /api/v1/delivery/estimate_time`

### 3) Пример запроса (curl)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/delivery/estimate_time" ^
  -H "Content-Type: application/json" ^
  -d "{\"distance\":12.5,\"hour\":18,\"day_of_week\":5,\"items_count\":3}"
```

Пример ответа:

```json
{"estimated_minutes": 45.0}
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