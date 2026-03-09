@echo off
echo ========================================
echo Настройка проекта для Лабораторной работы №2
echo ========================================
echo.

echo [1/5] Установка зависимостей...
poetry install
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить зависимости
    exit /b 1
)
echo.

echo [2/5] Запуск MinIO через Docker Compose...
docker-compose up -d
if errorlevel 1 (
    echo ОШИБКА: Не удалось запустить MinIO
    exit /b 1
)
echo Ожидание готовности MinIO (40 секунд)...
timeout /t 40 /nobreak >nul
echo.

echo [3/5] Инициализация DVC (если еще не инициализирован)...
if not exist .dvc (
    dvc init
    if errorlevel 1 (
        echo ОШИБКА: Не удалось инициализировать DVC
        exit /b 1
    )
)
echo.

echo [4/5] Настройка DVC remote...
dvc remote add -d myremote s3://datasets 2>nul
dvc remote modify myremote endpointurl http://localhost:9000
dvc remote modify myremote access_key_id minioadmin
dvc remote modify myremote secret_access_key minioadmin
echo.

echo [5/6] Генерация файла user_history.csv...
if not exist data\user_history.csv (
    poetry run python scripts/generate_user_history.py --rows 100 --seed 42
    if errorlevel 1 (
        echo ОШИБКА: Не удалось сгенерировать файл
        exit /b 1
    )
) else (
    echo Файл user_history.csv уже существует, пропускаем генерацию
)
echo.

echo [6/6] Добавление данных в DVC...
call scripts\prepare_data.bat
echo.

echo ========================================
echo Настройка завершена успешно!
echo ========================================
echo.
echo MinIO Console доступна по адресу: http://localhost:9001
echo Логин: minioadmin
echo Пароль: minioadmin
echo.
echo Для проверки работы выполните: scripts\demo.bat
echo.
