@echo off
title Business Card Extractor App (Virtual Environment)
echo ========================================================
echo   CARD VISIT EXTRACTOR (Desktop, Mobile and Android App)
echo ========================================================
echo.

IF NOT EXIST "venv\Scripts\python.exe" (
    echo Creating Virtual Environment venv...
    python -m venv venv
    echo Installing dependencies into venv...
    call venv\Scripts\python.exe -m pip install -r backend\requirements.txt
)

echo Activating Virtual Environment...
call venv\Scripts\activate.bat

echo.
echo Starting Backend Server on http://localhost:8000 ...
echo (Opening web browser automatically...)
start http://localhost:8000

venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
pause
