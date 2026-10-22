# Agent Instructions

## Mandatory Source of Truth

- Read `docs/PROJECT_SOURCE_OF_TRUTH.md` before changing architecture,
  runtime paths, ML behavior, releases, or project status.
- The product is the PySide6 desktop program in `packages/desktop/`. It calls
  the shared service layer in `apps/api/app/services` in-process over SQLite.
- The paused web app, its deploy setup, the Tkinter GUI, the TUI and the legacy
  `src/therapist_backend` / `src/clinical_workflow` API were removed on
  2026-10-23 (git tag `web-app-final`). Do not recreate them.
- Never commit `dist/`, `.local/`, `node_modules/`, `__pycache__/`, models, or
  audio files.

## Package Manager
- Python uses `venv` + `pip`:
  `python3.12 -m venv .venv312 && source .venv312/bin/activate`, then
  `pip install -r requirements.txt -r apps/api/requirements.txt -r requirements-desktop.txt`.
- Supported Python: 3.11–3.13 (3.12 recommended).

## Project Layout
- `packages/desktop/`: the desktop program (`ui/` windows, `core/` DesktopService and workspace).
- `apps/api/`: shared service layer; its FastAPI routes and tests are kept because the tests cover the services.
- `src/audio_pipeline/`, `src/clinical_speech/`, `packages/features/`, `packages/cha/`: ASR, Thai LSA rules, measures, CHAT.
- `scripts/evaluate_*.py` → `reports/metrics/`: evaluation evidence used by the term paper.
- `packages/ml/`, `scripts/ml/`, `reports/ml/`: earlier ML research (reference evidence, Gate 1).
- `site/`: download page on GitHub Pages.

## Clinical Safety Boundary
- This is a research/education prototype, not a diagnostic tool.
- Do not add text or flows that imply automated ASD diagnosis or Thai clinical validation.
- Keep real child names, surnames, direct identifiers, transcript text, audio bytes, and storage keys out of logs, fixtures, and committed data.
- Preserve consent gates, audit events and report safety checks in the service layer.

## Commands
| Task | Command |
|------|---------|
| Run the desktop program | `./run_gui.sh` (`--demo` for seeded demo data) |
| Python test file | `PYTHONPATH=apps/api:src pytest tests/test_name.py -q` |
| All Python tests | `bash scripts/check_project.sh` |
| Audio tests | `pytest -m audio` |
| Build the macOS .dmg | `python scripts/build_macos_dmg.py` |

On macOS run `tests/test_desktop*.py` (Qt) in a separate pytest process from
the rest, as `scripts/check_project.sh` does.

## Key Conventions
- Follow `README.md`, `DEVELOPER_SETUP.md`, `docs/DEVELOPMENT.md`, and `docs/SECURITY.md`.
- Update `README.md` when setup, project structure, major dependencies, or user-facing behavior changes.
- Update `CHANGELOG.md` only for real system behavior changes; docs-only edits do not require a version bump.
- Keep Python reference datasets and generated reports auditable; do not silently rewrite raw TalkBank/CHILDES source files.
- Releases need the project owner's approval (`docs/DESKTOP_RELEASE.md`).

## Commit Attribution
AI commits MUST include:
```
Co-Authored-By: (the agent model's name and attribution byline)
```
