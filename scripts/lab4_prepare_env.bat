@echo off
setlocal
cd /d "%~dp0.."
echo [ЛР4] Корень проекта: %CD%
if exist .env (
  echo Файл .env уже существует — пропуск копирования.
) else (
  if not exist .env.example (
    echo ОШИБКА: нет .env.example
    exit /b 1
  )
  copy /Y .env.example .env
  echo Создан .env из .env.example — отредактируйте при необходимости.
)
exit /b 0
