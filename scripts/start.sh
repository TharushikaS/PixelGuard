#!/bin/bash
# PixelGuard local startup (macOS / Linux).
# Assumes:
#   - MongoDB is running on $MONGODB_URL (default mongodb://localhost:27017)
#   - Python 3.10+ and Node 18+ are on PATH
#
# Usage: bash scripts/start.sh

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "PixelGuard - local startup"
echo "=========================="

# ---- Python venv ----
if [ ! -d "backend/.venv" ]; then
  echo "[1/4] Creating Python venv..."
  python3 -m venv backend/.venv
fi

# shellcheck disable=SC1091
source backend/.venv/bin/activate
pip install --quiet -r backend/requirements.txt

# ---- .env ----
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "[!] Created backend/.env from example — edit MONGODB_URL if needed."
fi

# ---- Mongo indexes ----
echo "[2/4] Ensuring MongoDB indexes..."
python scripts/setup_db.py

# ---- Backend ----
echo "[3/4] Starting FastAPI on :8000 ..."
( cd backend && uvicorn app.main:app --reload --port 8000 ) &
BACKEND_PID=$!

# ---- Frontend ----
echo "[4/4] Installing & starting React on :3000 ..."
( cd frontend && (npm install --silent && npm start) ) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" INT TERM EXIT

echo ""
echo "Frontend: http://localhost:3000"
echo "Backend : http://localhost:8000"
echo "Docs    : http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."
wait
