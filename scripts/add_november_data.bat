@echo off
echo ========================================
echo Добавление данных за ноябрь (версия v2.0)
echo ========================================
echo.

echo Добавление новых данных о просмотрах за ноябрь в user_history.csv...
echo 6,1 >> data\user_history.csv
echo 6,7 >> data\user_history.csv
echo 7,2 >> data\user_history.csv
echo 7,8 >> data\user_history.csv
echo 8,3 >> data\user_history.csv
echo 8,9 >> data\user_history.csv
echo 1,10 >> data\user_history.csv
echo 2,11 >> data\user_history.csv
echo.

echo Обновление версии в DVC (v2.0 - ноябрь)...
dvc add data/user_history.csv
if errorlevel 1 (
    echo ОШИБКА: Не удалось обновить версию в DVC
    exit /b 1
)
echo.

echo Отправка новой версии в MinIO...
dvc push
if errorlevel 1 (
    echo ОШИБКА: Не удалось отправить данные в MinIO
    exit /b 1
)
echo.

echo ========================================
echo Новая версия данных создана и отправлена!
echo Версия v2.0 (октябрь + ноябрь) зафиксирована
echo ========================================
echo.
echo Для переключения между версиями используйте:
echo   dvc checkout data/user_history.csv.dvc
echo.
