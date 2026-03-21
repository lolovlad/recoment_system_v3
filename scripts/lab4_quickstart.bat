@echo off
setlocal
cd /d "%~dp0.."
echo ========================================
echo  ЛР4 — быстрый сценарий (Windows)
echo ========================================
call scripts\lab4_prepare_env.bat || exit /b 1
call scripts\lab4_ensure_data.bat || exit /b 1
call scripts\lab4_train_recommendation.bat || exit /b 1
echo.
echo Запуск Docker (redis, api, worker, minio)...
call scripts\lab4_docker_up.bat || exit /b 1
echo.
echo Ожидание 15 секунд, пока поднимутся сервисы...
timeout /t 15 /nobreak >nul
echo.
echo Автопроверка API...
poetry run python scripts/lab4_verify.py
exit /b %ERRORLEVEL%
