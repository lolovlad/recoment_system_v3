## Recommender System — ЛР1 + ЛР2

Проект демонстрирует скелет ИИ‑системы по принципам Clean Architecture и интеграцию слоя хранения данных с версионированием (DVC + MinIO).

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
```

> Для DVC доступ к MinIO на стенде настроен через `.dvc/config.local`, который **не попадает в Git**.

### Запуск MinIO (Docker Compose)

```bash
docker compose up -d
```

Будут подняты:

- сервис `minio` (S3‑совместимое хранилище, порты `9000` — API, `9001` — Console)
- сервис `minio-init`, который автоматически создаёт бакет `datasets`

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