#!/bin/bash
# Local orchestrator script to run both FastAPI backend and React frontend clinician app.

set -e

# ANSI colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BLUE}=== Starting Local PasaScope App (Frontend + Backend) ===${NC}"

# 1. Point the frontend at the local API.
# Passed as an environment variable rather than written to .env.local, which
# the repository consistency check treats as a local secret file.
FRONTEND_DIR="apps/pasascope-app"
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000/api/v1}"

echo -e "${BLUE}[1/4] Configuring local environment variables...${NC}"
echo -e "${GREEN}✓ Frontend will call $NEXT_PUBLIC_API_BASE_URL${NC}"

# 2. Check Node dependencies
echo -e "${BLUE}[2/4] Checking Node dependencies...${NC}"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "node_modules not found. Running npm install..."
    (cd "$FRONTEND_DIR" && npm install)
else
    echo -e "${GREEN}✓ Node modules already installed.${NC}"
fi

# 3. Start Backend FastAPI
echo -e "${BLUE}[3/4] Starting FastAPI Backend on port 8000...${NC}"
if [ -d ".venv312" ]; then
    # shellcheck disable=SC1091
    source .venv312/bin/activate
elif [ -d ".venv" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
else
    echo -e "${YELLOW}[Warning] No .venv312 or .venv found. Using system Python.${NC}"
fi

# On-device speech recognition is opt-in; export this before running the script.
if [ "${PASASCOPE_ASR_LOCAL_WHISPER_ENABLED:-false}" = "true" ]; then
    echo -e "${GREEN}✓ Local Whisper transcription enabled (model: ${PASASCOPE_ASR_WHISPER_MODEL_SIZE:-medium}).${NC}"
else
    echo -e "${YELLOW}Local Whisper transcription is off. Set PASASCOPE_ASR_LOCAL_WHISPER_ENABLED=true to transcribe recordings.${NC}"
fi

# Run uvicorn in the background and save PID
(cd apps/api && PYTHONPATH=.:../..:../../src uvicorn app.main:app --host 127.0.0.1 --port 8000) > backend.log 2>&1 &
BACKEND_PID=$!

# Trap Ctrl+C (SIGINT) and SIGTERM to kill the backend PID when this script is stopped
cleanup() {
    echo -e "\n${YELLOW}Stopping FastAPI Backend (PID: $BACKEND_PID)...${NC}"
    kill "$BACKEND_PID" || true
    echo -e "${GREEN}Cleanup finished. Bye!${NC}"
}
trap cleanup EXIT SIGINT SIGTERM

# Give the backend a second to boot up
sleep 1.5
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "\033[0;31mError: FastAPI backend failed to start. Check backend.log for details.\033[0m"
    exit 1
fi
echo -e "${GREEN}✓ Backend is running (PID: $BACKEND_PID). Logs written to backend.log${NC}"

# 4. Start React Frontend
echo -e "${BLUE}[4/4] Starting React Frontend...${NC}"
cd "$FRONTEND_DIR"
npm run dev
