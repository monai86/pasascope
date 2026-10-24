#!/bin/bash
set -eo pipefail
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

select_python_runtime() {
    local candidate
    local candidates=()

    if [ -n "${PASASCOPE_PYTHON:-${LINGUALENS_PYTHON:-}}" ]; then
        candidates+=("${PASASCOPE_PYTHON:-$LINGUALENS_PYTHON}")
    fi
    candidates+=(".venv/bin/python")
    for candidate in .venv*/bin/python; do
        candidates+=("$candidate")
    done
    candidates+=("python3.12" "python3.13" "python3.11" "python3")

    for candidate in "${candidates[@]}"; do
        if { [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; } \
            && "$candidate" "$(dirname "$0")/check_python_runtime.py" >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

if ! PYTHON_BIN="$(select_python_runtime)"; then
    echo "Error: PasaScope requires Python >=3.11,<3.14; Python 3.12 is recommended." >&2
    exit 2
fi

"$PYTHON_BIN" "$(dirname "$0")/check_python_runtime.py"

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0;0m' # No Color

echo -e "${BLUE}=== Starting Focused Local Project Verification ===${NC}"

echo -e "${BLUE}[0/4] Checking repository source-of-truth consistency...${NC}"
find . -name ".DS_Store" -not -path "./.venv*" -delete 2>/dev/null || true
"$PYTHON_BIN" scripts/check_repo_consistency.py

echo -e "${BLUE}[1/4] Running local secret scan...${NC}"
"$PYTHON_BIN" scripts/security_scan.py

echo -e "${BLUE}[2/4] Checking that the core modules import (Python: $PYTHON_BIN)...${NC}"
python_imports=(
    "app.services.report_service"
    "app.services.transcript_service"
    "packages.desktop.core"
    "src.audio_pipeline.chat_formatter"
    "src.audio_pipeline.chatter_validator"
    "src.audio_pipeline.segmentation"
    "src.audio_pipeline.whisper_transcribe"
    "src.clinical_speech.thai_lsa"
)

for mod in "${python_imports[@]}"; do
    echo -n "  Checking import of $mod... "
    if PYTHONPATH=.:apps/api:src "$PYTHON_BIN" -c "import $mod" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo -e "${RED}Error: Failed to import $mod. Check dependencies or syntax.${NC}"
        exit 1
    fi
done

echo -e "${BLUE}[3/4] Running Python tests (excluding heavy audio)...${NC}"
if "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
    # Qt tests run in their own process; mixing them with the rest has hung on macOS.
    PYTHONPATH=apps/api:src "$PYTHON_BIN" -m pytest apps/api/tests -m "not audio" -q
    PYTHONPATH=apps/api:src "$PYTHON_BIN" -m pytest tests/test_desktop*.py -q
    PYTHONPATH=apps/api:src "$PYTHON_BIN" -m pytest tests --ignore-glob="tests/test_desktop*.py" -m "not audio" -q
    echo -e "${GREEN}✓ All core Python tests passed.${NC}"
else
    echo -e "${RED}Error: pytest is not installed in the current Python environment.${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== Focused local project verification passed. ===${NC}"
echo -e "${YELLOW}This check does not run dependency audits, the Python version matrix or audio tests. CI runs the version matrix and the audit.${NC}"
exit 0
