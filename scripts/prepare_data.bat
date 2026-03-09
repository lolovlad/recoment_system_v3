@echo off
echo ========================================
echo Подготовка данных для DVC
echo ========================================
echo.

echo Проверка наличия user_history.csv...
if not exist data\user_history.csv (
    echo ОШИБКА: Файл data\user_history.csv не найден!
    exit /b 1
)
echo.

echo Добавление user_history.csv в DVC (версия v1.0 - октябрь)...
dvc add data/user_history.csv
if errorlevel 1 (
    echo ОШИБКА: Не удалось добавить файл в DVC
    exit /b 1
)
echo.

echo Отправка данных в MinIO...
dvc push
if errorlevel 1 (
    echo ПРЕДУПРЕЖДЕНИЕ: Не удалось отправить данные в MinIO
    echo Убедитесь, что MinIO запущен и бакет создан
)
echo.

echo ========================================
echo Подготовка данных завершена!
echo Версия v1.0 (октябрь) зафиксирована в DVC
echo ========================================
