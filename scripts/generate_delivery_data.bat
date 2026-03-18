@echo off
setlocal

REM Generate synthetic dataset for Lab 3
poetry run python scripts/generate_delivery_data.py --rows 5000 --seed 42 --output data/delivery_train.csv

