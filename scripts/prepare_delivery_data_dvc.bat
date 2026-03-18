@echo off
setlocal

REM Put delivery_train.csv under DVC and push to remote
REM Assumes DVC remote already configured and MinIO is running.

IF NOT EXIST data\delivery_train.csv (
  echo Dataset not found: data\delivery_train.csv
  echo Generate it first: scripts\generate_delivery_data.bat
  exit /b 1
)

dvc add data\delivery_train.csv
dvc push

echo Done. DVC file created/updated: data\delivery_train.csv.dvc

