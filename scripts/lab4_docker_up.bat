@echo off
setlocal
cd /d "%~dp0.."
echo [ЛР4] Сборка и запуск: redis, api, worker, minio...
docker compose up --build -d
if errorlevel 1 exit /b 1
echo.
echo Готово. API: http://127.0.0.1:8000/docs
echo Redis: localhost:6379
exit /b 0
