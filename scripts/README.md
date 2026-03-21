# Скрипты лабораторной работы №2

Скрипты выстроены в порядке использования: сначала генерация данных, затем настройка и работа с версиями.

**Переменные окружения:** общий файл **`.env`** в корне репозитория (шаблон — **`.env.example`**). Загрузка в Python через `recommender_system.env.load_project_env()` (см. корневой `README.md`).

**Где что по моделям:**

- **Рекомендательная система (ЛР1–2 + ЛР4):** обучение — **`train_recommendation_model.py`** → **`models/recommendation.onnx`** + **`models/recommendation_meta.json`** из **`data/user_history.csv`**, опционально upload в MinIO. Инференс в worker: ONNX Runtime + JSON; синк с MinIO при отсутствии файлов.
- **Время доставки (ЛР3, ONNX):** обучение — **`train_delivery_model.py`** / **`train_model.bat`** (bat оставлено старым именем) → `models/delivery_estimator.onnx` из **`data/delivery_train.csv`** (`generate_delivery_data.py`). Инференс: `tasks.py` → `estimate_delivery_task`.

### ЛР4 — скрипты запуска и проверки

| Файл | Назначение |
|------|------------|
| `lab4_prepare_env.bat` | Копия `.env.example` → `.env` |
| `lab4_ensure_data.bat` | Проверка/генерация `data/user_history.csv` |
| `lab4_train_recommendation.bat` | Обучение `recommendation.onnx` + meta |
| `lab4_docker_up.bat` | `docker compose up --build -d` |
| `lab4_verify.py` | Автопроверка API (Python): `poetry run python scripts/lab4_verify.py [URL] [user_id]` |
| `lab4_verify.ps1` | То же в PowerShell |
| `lab4_run_tests.bat` | Pytest: тесты ЛР4 + обучение рекомендаций |
| `lab4_quickstart.bat` | Цепочка: env → данные → обучение → Docker → verify |

Пошаговый сценарий см. в корневом **README.md** (раздел «ЛР4 — пошаговый гайд»).

---

## 1. Генерация данных

### generate_user_history.py / generate_user_history.bat

Создаёт файл `data/user_history.csv` с колонками `user_id` и `item_id` (история взаимодействий пользователей с товарами). Выполнять **до** добавления данных в DVC.

**Параметры:**
- `--rows` — количество строк (по умолчанию: 100)
- `--seed` — seed для воспроизводимости
- `--output` — путь к файлу (по умолчанию: `data/user_history.csv`)

**Примеры:**
```bash
# Интерактивный режим (bat)
scripts\generate_user_history.bat

# С параметрами
scripts\generate_user_history.bat 100 42
scripts\generate_user_history.bat 50

# Через Python
poetry run python scripts/generate_user_history.py --rows 100 --seed 42
poetry run python scripts/generate_user_history.py --rows 50
poetry run python scripts/generate_user_history.py
```

**Формат данных:**
```csv
user_id,item_id
1,5
1,12
2,3
...
```

Папка `data` создаётся автоматически, если её нет.

---

## ЛР3 — Датасет и обучение модели (регрессия доставки)

### 1) Генерация датасета (отдельно от обучения)

#### generate_delivery_data.py / generate_delivery_data.bat

Создаёт файл `data/delivery_train.csv` с признаками:

- `distance` (float)
- `hour` (int)
- `day_of_week` (int)
- `items_count` (int)
- `delivery_minutes` (target)

Запуск:

```bash
scripts\generate_delivery_data.bat

# или через Python:
poetry run python scripts/generate_delivery_data.py --rows 5000 --seed 42 --output data/delivery_train.csv
```

### 2) Добавление/обновление датасета в DVC (как в ЛР2)

#### prepare_delivery_data_dvc.bat

Ставит `data/delivery_train.csv` под контроль DVC и пушит в remote (MinIO):

```bash
scripts\prepare_delivery_data_dvc.bat
```

Ручные команды (аналогично `user_history.csv`):

```bash
dvc add data/delivery_train.csv
dvc push
```

Чтобы добавить **новый датасет** (другой файл), делаете то же самое:

```bash
dvc add data/<new_dataset>.csv
dvc push
```

### 3) Обучение рекомендаций (TruncatedSVD → ONNX + JSON)

#### train_recommendation_model.py / train_recommendation_model.bat

По **`data/user_history.csv`** обучает `TruncatedSVD`, экспортирует скоринг в **`models/recommendation.onnx`**, метаданные — **`models/recommendation_meta.json`**, при настроенном MinIO загружает оба файла в бакет `models`.

```bash
scripts\train_recommendation_model.bat
poetry run python scripts/train_recommendation_model.py --data data/user_history.csv --out models/recommendation.onnx --out-meta models/recommendation_meta.json
```

### 4) Обучение и экспорт модели доставки (ONNX) + авто‑upload в MinIO

#### train_delivery_model.py / train_model.bat

Скрипт обучает модель **из CSV** `data/delivery_train.csv`, сохраняет ONNX в `models/delivery_estimator.onnx` и затем (при наличии env) автоматически загружает модель в MinIO в бакет `models`.

```bash
scripts\train_model.bat

# или:
poetry run python scripts/train_delivery_model.py --seed 42 --data data/delivery_train.csv
```

---

## 2. Первичная настройка

### setup.bat

Полная автоматическая настройка проекта (запускать после генерации данных при необходимости):

- Установка зависимостей (`poetry install`)
- Запуск MinIO (`docker compose up -d`)
- Инициализация DVC и настройка remote
- Генерация `user_history.csv`, если файла ещё нет
- Добавление данных в DVC (версия v1.0 — октябрь) и отправка в MinIO

```bash
scripts\setup.bat
```

---

## 3. Подготовка и отправка данных в DVC/MinIO

### prepare_data.bat

Добавляет текущий `data/user_history.csv` в DVC и отправляет в MinIO. Использовать после изменений в данных.

```bash
scripts\prepare_data.bat
```

---

## 4. Проверка работы системы

### demo.bat

Демонстрация работы: проверка MinIO, конфигурации DVC и скрипта инициализации данных.

```bash
scripts\demo.bat
```

---

## 5. Версия v2.0 (добавление данных за ноябрь)

### add_november_data.bat

Добавляет данные за ноябрь в `user_history.csv`, обновляет версию в DVC (v2.0) и отправляет в MinIO.

```bash
scripts\add_november_data.bat
```

---

## 6. Переключение между версиями данных

### switch_to_october.bat

Переключение на версию v1.0 (только октябрь).

```bash
scripts\switch_to_october.bat
```

### switch_to_november.bat

Переключение на версию v2.0 (октябрь + ноябрь).

```bash
scripts\switch_to_november.bat
```

---

## 7. Очистка и сброс

### clean_and_reset.bat

Остановка MinIO, удаление локальных данных и подготовка к перезапуску с нуля.

```bash
scripts\clean_and_reset.bat
```

---

## Последовательность проверки (кратко)

1. **Генерация данных:** `scripts\generate_user_history.bat` (или с параметрами).
2. **Настройка:** `scripts\setup.bat`.
3. **Проверка:** `scripts\demo.bat`.
4. **Версия v2.0:** `scripts\add_november_data.bat`.
5. **Переключение версий:** `scripts\switch_to_october.bat` / `scripts\switch_to_november.bat`.

---

## Ручная настройка (без .bat)

После настройки DVC remote:

1. Сгенерировать данные:
   ```bash
   poetry run python scripts/generate_user_history.py --rows 100 --seed 42
   ```
2. Добавить в DVC и отправить в MinIO:
   ```bash
   dvc add data/user_history.csv
   dvc push
   ```

---

## Версии данных

- **v1.0 (октябрь):** только данные за октябрь  
- **v2.0 (октябрь + ноябрь):** данные за октябрь и ноябрь
