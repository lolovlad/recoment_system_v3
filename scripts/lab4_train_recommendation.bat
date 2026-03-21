@echo off
setlocal
cd /d "%~dp0.."
echo [ЛР4] Обучение рекомендаций: user_history.csv -^> recommendation.onnx + meta.json
call scripts\train_recommendation_model.bat
exit /b %ERRORLEVEL%
