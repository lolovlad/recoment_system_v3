# Скрипты проекта

Скрипты ориентированы на рекомендательную систему: подготовка данных, обучение модели и проверка ЛР4-сценария.

Переменные окружения читаются из `.env` в корне репозитория.

## Основные скрипты ЛР4

| Файл | Назначение |
|------|------------|
| `lab4_prepare_env.bat` | Проверка/подготовка `.env` |
| `lab4_ensure_data.bat` | Проверка/генерация `data/user_history.csv` |
| `lab4_train_recommendation.bat` | Обучение `recommendation.onnx` + `recommendation_meta.json` |
| `lab4_docker_up.bat` | `docker compose up --build -d` |
| `lab4_verify.py` | Проверка API (POST/GET рекомендаций) |
| `lab4_verify.ps1` | То же в PowerShell |
| `lab4_run_tests.bat` | Запуск тестов ЛР4 |
| `lab4_quickstart.bat` | Полная цепочка: env -> данные -> обучение -> docker -> verify |

## Генерация данных рекомендаций

`generate_user_history.py` / `generate_user_history.bat` создают `data/user_history.csv`.

Пример:

```bash
poetry run python scripts/generate_user_history.py --rows 100 --seed 42 --output data/user_history.csv
```

## Обучение модели рекомендаций

`train_recommendation_model.py` / `train_recommendation_model.bat` обучают `TruncatedSVD` и экспортируют:
- `models/recommendation.onnx`
- `models/recommendation_meta.json`

Пример:

```bash
poetry run python scripts/train_recommendation_model.py --data data/user_history.csv --out models/recommendation.onnx --out-meta models/recommendation_meta.json --components 32 --seed 42
```

## DVC-утилиты

- `setup.bat`
- `prepare_data.bat`
- `add_november_data.bat`
- `switch_to_october.bat`
- `switch_to_november.bat`
- `demo.bat`
- `clean_and_reset.bat`
