#!/usr/bin/env bash
# SponsorPulse Local Development Launcher (macOS/Linux)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo " ========================================"
echo "  SponsorPulse - Local Dev Environment"
echo " ========================================"
echo ""

# --- Backend Setup ---
echo "[1/4] Setting up Python virtual environment..."
cd "$SCRIPT_DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "[2/4] Installing backend dependencies..."
pip install -r requirements.txt --quiet

echo "[3/4] Initializing database tables..."
python -c "from app.core.database import init_db; init_db()"

# --- Frontend Setup ---
echo "[4/4] Installing frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
npm install --silent

echo ""
echo " ========================================"
echo "  Starting servers..."
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo " ========================================"
echo ""

# Start backend in background
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend in foreground
cd "$SCRIPT_DIR/frontend"
npm run dev

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null

