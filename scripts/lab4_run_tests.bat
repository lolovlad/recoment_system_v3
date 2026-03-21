@echo off
setlocal
cd /d "%~dp0.."
echo [ЛР4] Pytest: сценарии API, worker, интеграция...
poetry run pytest tests/test_lab4_recommendations_api.py tests/test_lab4_worker.py tests/test_lab4_integration.py tests/test_train_recommendation_model.py -v
exit /b %ERRORLEVEL%
