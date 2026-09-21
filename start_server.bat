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

set PORT=8000

REM Allow any host header so other devices can reach the server by IP.
REM (Environment variables set here take priority over the .env file.)
set ALLOWED_HOSTS=*

REM Open the firewall port for the local network (needs Administrator; skipped if it fails).
netsh advfirewall firewall show rule name="POS System %PORT%" >nul 2>&1
if errorlevel 1 (
    netsh advfirewall firewall add rule name="POS System %PORT%" dir=in action=allow protocol=TCP localport=%PORT% profile=private,domain >nul 2>&1
    if errorlevel 1 (
        echo NOTE: Could not open firewall port %PORT%. Right-click this file and
        echo       "Run as administrator" once if other devices cannot connect.
        echo.
    )
)

echo.
echo Collecting static files check skipped (DEBUG mode serves static automatically).
echo.
echo ============================================
echo   Starting Django development server
echo   This computer : http://127.0.0.1:%PORT%/
echo   Other devices on the same network:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=* delims= " %%b in ("%%a") do echo       http://%%b:%PORT%/
)
echo   Press CTRL+C to stop the server.
echo ============================================
echo.

python manage.py runserver 0.0.0.0:%PORT%

endlocal
pause
