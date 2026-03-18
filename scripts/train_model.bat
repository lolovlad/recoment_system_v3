@echo off
setlocal

REM Train and export ONNX model
poetry run python scripts/train_model.py --seed 42 --data data/delivery_train.csv

