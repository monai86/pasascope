#!/usr/bin/env bash
# Assemble the files a Hugging Face Space needs to run the PasaScope API.
#
#   scripts/build_hf_space_bundle.sh [output-dir]
#
# The bundle holds the API, the audio pipeline and the small artifacts the API
# reads. It leaves out the research corpora under data/ (hundreds of MB that
# the API never opens) and everything the web app needs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/.local/hf-space-bundle}"

rm -rf "$OUT"
mkdir -p "$OUT/apps/api" "$OUT/artifacts" "$OUT/data"

copy_tree() { # copy_tree <source> <destination>, without caches or tests
  rsync -a --exclude '__pycache__' --exclude '*.pyc' --exclude 'tests' --exclude '.pytest_cache' "$1" "$2"
}

cp "$ROOT/deploy/hf-space/Dockerfile" "$ROOT/deploy/hf-space/README.md" "$OUT/"
cp "$ROOT/requirements.txt" "$OUT/requirements.txt"
cp "$ROOT/apps/api/requirements.txt" "$ROOT/apps/api/alembic.ini" "$ROOT/apps/api/alembic-assessment.ini" "$OUT/apps/api/"
copy_tree "$ROOT/apps/api/app" "$OUT/apps/api/"
copy_tree "$ROOT/src" "$OUT/"
copy_tree "$ROOT/packages" "$OUT/"
copy_tree "$ROOT/artifacts/reference_evidence" "$OUT/artifacts/"
for file in model_card_v2.md feature_schema.json screening_model.joblib; do
  [ -f "$ROOT/artifacts/$file" ] && cp "$ROOT/artifacts/$file" "$OUT/artifacts/"
done
[ -d "$ROOT/data/demo" ] && copy_tree "$ROOT/data/demo" "$OUT/data/"

echo "Bundle written to $OUT ($(du -sh "$OUT" | cut -f1))"
