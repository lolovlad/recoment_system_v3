@echo off
setlocal
REM Обучение модели рекомендаций по data/user_history.csv (ЛР1-2)
poetry run python scripts/train_recommendation_model.py --data data/user_history.csv --out models/recommendation.onnx --out-meta models/recommendation_meta.json --components 32 --seed 42
