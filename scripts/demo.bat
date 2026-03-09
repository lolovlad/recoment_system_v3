@echo off
echo ========================================
echo Демонстрация работы системы
echo ========================================
echo.

echo [1/4] Проверка работы MinIO...
docker-compose ps
echo.

echo [2/4] Проверка DVC конфигурации...
dvc remote list
echo.

echo [3/4] Проверка версионированных данных...
dvc list data/
echo.

echo [4/4] Запуск скрипта инициализации данных...
poetry run python scripts/init_data.py
echo.

echo ========================================
echo Демонстрация завершена!
echo ========================================
echo.
echo Для просмотра данных в MinIO:
echo 1. Откройте http://localhost:9001
echo 2. Войдите с учетными данными: minioadmin / minioadmin
echo 3. Перейдите в бакет "datasets"
echo.
