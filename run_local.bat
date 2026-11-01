@echo off
REM SponsorPulse Local Development Launcher (Windows)
echo.
echo  ========================================
echo   SponsorPulse - Local Dev Environment
echo  ========================================
echo.

REM --- Backend Setup ---
echo [1/4] Setting up Python virtual environment...
cd /d "%~dp0backend"
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [2/4] Installing backend dependencies...
pip install -r requirements.txt --quiet

echo [3/4] Initializing database tables...
python -c "from app.core.database import init_db; init_db()"

REM --- Frontend Setup ---
echo [4/4] Installing frontend dependencies...
cd /d "%~dp0frontend"
call npm install --silent

echo.
echo  ========================================
echo   Starting servers...
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo  ========================================
echo.

REM Start backend in a new window
start "SponsorPulse Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

REM Start frontend in this window
cd /d "%~dp0frontend"
npm run dev

