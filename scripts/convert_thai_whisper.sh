#!/usr/bin/env bash
# Convert the Thai fine-tuned Whisper model (Thonburian Whisper,
# biodatlab/whisper-th-medium-combined, Apache-2.0) to the CTranslate2 format
# that faster-whisper loads. The Hugging Face repository only ships
# transformers weights (model.safetensors), so faster-whisper cannot open it
# directly.
#
# The converter needs transformers and torch, which the API does not. They are
# installed into a throwaway virtual environment under .local/ so the project
# environment stays unchanged.
#
# Usage:
#   bash scripts/convert_thai_whisper.sh [output_dir] [source_model]
#
# Default output: models/whisper-th-medium-combined-ct2 (ignored by git).
# The API finds it there, or at PASASCOPE_ASR_THAI_MODEL_PATH.
#
# Another Thai Whisper can be converted for comparison, e.g. Typhoon Whisper
# Turbo (typhoon-ai/typhoon-whisper-turbo, MIT):
#   bash scripts/convert_thai_whisper.sh models/typhoon-whisper-turbo-ct2 typhoon-ai/typhoon-whisper-turbo
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT/models/whisper-th-medium-combined-ct2}"
SOURCE_MODEL="${2:-biodatlab/whisper-th-medium-combined}"
VENV="$ROOT/.local/venvs/ct2-convert"
PYTHON="${PYTHON:-$ROOT/.venv312/bin/python}"

if [ -f "$OUTPUT_DIR/model.bin" ]; then
  echo "Already converted: $OUTPUT_DIR"
  exit 0
fi

if [ ! -x "$VENV/bin/python" ]; then
  "$PYTHON" -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "ctranslate2>=4.4" "transformers>=4.44,<5" torch

"$VENV/bin/ct2-transformers-converter" \
  --model "$SOURCE_MODEL" \
  --output_dir "$OUTPUT_DIR" \
  --copy_files tokenizer.json preprocessor_config.json \
  --quantization float16

echo "Converted $SOURCE_MODEL to $OUTPUT_DIR"
