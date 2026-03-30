@echo off
setlocal
cd /d "%~dp0.."
echo [ЛР4] Корень проекта: %CD%
if exist .env (
  echo Файл .env уже существует.
) else (
  type nul > .env
  echo Создан пустой .env. Заполните переменные перед запуском.
)
exit /b 0
