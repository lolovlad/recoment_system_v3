@echo off
echo ========================================
echo Полная очистка и перезапуск проекта
echo ========================================
echo.

echo [1/4] Остановка и удаление контейнеров MinIO...
docker-compose down -v
if errorlevel 1 (
    echo ПРЕДУПРЕЖДЕНИЕ: Не удалось остановить контейнеры
)
echo.

echo [2/4] Удаление локальных данных (user_history.csv)...
if exist data\user_history.csv (
    del /f data\user_history.csv
    echo Файл user_history.csv удален
)
echo.

echo [3/4] Удаление DVC кэша (опционально)...
if exist .dvc\cache (
    echo Удаление кэша DVC...
    rmdir /s /q .dvc\cache
)
echo.

echo [4/4] Запуск заново...
call scripts\setup.bat
echo.

echo ========================================
echo Очистка и перезапуск завершены!
echo ========================================
