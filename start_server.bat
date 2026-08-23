@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   POS System - Update and Start
echo ============================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Is Python installed and on PATH?
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo.
echo Installing/updating dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Applying database migrations...
python manage.py migrate
if errorlevel 1 (
    echo Migration failed. Check your MySQL connection and .env settings.
    pause
    exit /b 1
)

echo.
echo Collecting static files check skipped (DEBUG mode serves static automatically).
echo.
echo ============================================
echo   Starting Django development server
echo   Visit http://127.0.0.1:8000/
echo   Press CTRL+C to stop the server.
echo ============================================
echo.

python manage.py runserver

endlocal
pause
