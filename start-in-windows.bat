@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM start-in-windows.bat
REM ----------------------------------------------------------------------------
REM One-click launcher for the K-Panel demo on Windows.
REM
REM What it does, in order:
REM   1. Makes sure Python 3 is installed (installs it via winget if missing).
REM   2. Creates a local virtual environment (.\venv) if it doesn't exist yet.
REM   3. Installs/updates the Python dependencies needed by k-panel.py.
REM   4. Stops any previous "K-Panel Backend" window still holding the port.
REM   5. Starts the backend (k-panel.py) on http://127.0.0.1:8877
REM   6. Serves k-panel.html on http://127.0.0.1:8080 and opens it in your
REM      default browser.
REM
REM Just double-click this file in File Explorer.
REM ============================================================================

cd /d "%~dp0"

set BACKEND_PORT=8877
set STATIC_PORT=8080

echo == K-Panel setup (Windows) ==

REM --- Step 1: ensure Python 3 is available ---
where python >nul 2>nul
if errorlevel 1 (
    echo [setup] Python not found.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo [error] winget is not available, and Python was not found.
        echo         Please install Python 3 manually from https://python.org/downloads
        echo         and re-run this script.
        pause
        exit /b 1
    ) else (
        echo [setup] Installing Python 3 via winget...
        winget install -e --id Python.Python.3.12
    )
) else (
    echo [setup] Python found.
    python --version
)

REM --- Step 2: create a virtual environment if missing ---
if not exist "venv\" (
    echo [setup] Creating virtual environment...
    python -m venv venv
)

REM --- Step 3: install/update Python dependencies ---
echo [setup] Installing Python dependencies...
call venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check --upgrade pip
call venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r requirements.txt

REM --- Step 4: start the backend (FastAPI/uvicorn) ---
REM Port 8877 was chosen specifically because it isn't a well-known default
REM for any common service (unlike, say, 5432 which is PostgreSQL's default
REM port). To keep re-runs of this script safe, we only close a *previous
REM window launched by this same script* (matched by its window title
REM "K-Panel Backend"), never an arbitrary/unrelated process that might
REM happen to be using the port — that avoids accidentally killing something
REM like a real database.
echo [setup] Stopping any previous K-Panel backend window (if running)...
taskkill /FI "WINDOWTITLE eq K-Panel Backend*" /T /F >nul 2>nul

echo [run] Starting backend on http://127.0.0.1:%BACKEND_PORT% ...
start "K-Panel Backend" /min cmd /c "venv\Scripts\python.exe k-panel.py"

REM --- Step 5: serve the static HTML page and open it in the browser ---
echo [run] Serving k-panel.html on http://127.0.0.1:%STATIC_PORT% ...
start "K-Panel Static Server" /min cmd /c "venv\Scripts\python.exe -m http.server %STATIC_PORT% --directory ."

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:%STATIC_PORT%/k-panel.html"

echo.
echo K-Panel is running:
echo   Backend:  http://127.0.0.1:%BACKEND_PORT%
echo   Frontend: http://127.0.0.1:%STATIC_PORT%/k-panel.html
echo.
echo Close the "K-Panel Backend" and "K-Panel Static Server" windows to stop the servers.
pause
