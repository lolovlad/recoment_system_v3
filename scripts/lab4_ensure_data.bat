@echo off
setlocal
cd /d "%~dp0.."
if exist data\user_history.csv (
  echo [ЛР4] data\user_history.csv найден.
  exit /b 0
)
echo [ЛР4] Нет data\user_history.csv — генерация (200 строк, seed 42)...
if not exist data mkdir data
poetry run python scripts/generate_user_history.py --rows 200 --seed 42 --output data/user_history.csv
exit /b %ERRORLEVEL%
