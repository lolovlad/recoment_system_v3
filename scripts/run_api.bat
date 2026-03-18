@echo off
setlocal

REM Run FastAPI in development mode
poetry run uvicorn src.recommender_system.presentation.api:app --reload

