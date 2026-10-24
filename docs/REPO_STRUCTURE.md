# Repository Structure

[`PROJECT_SOURCE_OF_TRUTH.md`](./PROJECT_SOURCE_OF_TRUTH.md) holds the rules.
This file is the quick folder map.

## The program

| Path | What it is |
|---|---|
| `packages/desktop/` | The PySide6 desktop program: `app.py` (start), `ui/` (windows, pages, theme, PDF), `core/` (DesktopService, SQLite workspace, backup, updates, model downloads) |
| `apps/api/app/services/` | Shared service layer the desktop program calls in-process (transcripts, features, reports, consent, safety checks) |
| `apps/api/app/` (rest) | Database models, repository (SQLite through SQLAlchemy), schemas and settings used by the service layer |
| `src/audio_pipeline/` | Recording → transcript draft: VAD, Whisper, child/adult split, utterance boundaries, CHAT output |
| `src/clinical_speech/` | Thai LSA rules (`thai_lsa.py`), CHAT export, clinical feature extraction |
| `packages/features/` | Transcript, turn-taking, Thai POS and acoustic measures |
| `packages/cha/` | CHAT parser, round-trip check, Thai word list |
| `run_gui.sh`, `pasascope` | Launchers (`pasascope` is a link to `run_gui.sh`) |
| `site/` | Download page (GitHub Pages) |

## Evaluation and research

| Path | What it is |
|---|---|
| `scripts/evaluate_*.py` and related | Evaluation scripts; results go to `reports/metrics/` |
| `reports/metrics/` | Evaluation results cited by the term paper (`EVALUATION_SUMMARY.md` first) |
| `packages/ml/`, `scripts/ml/`, `reports/ml/`, `artifacts/` | Earlier ML work: reference-evidence model, Gate 1, model cards |
| `reports/clinical/`, `reports/human_actions/` | Protocols and checklists for a future Thai clinical pilot |
| `data/` | Public TalkBank transcripts, manifests, reference features, evaluation gold transcripts |
| `models/` | Local Whisper models (ignored by git except `README.md`) |
| `docs/literature/`, `docs/REFERENCES.md` | Literature notes and bibliography |

## Build and release

| Path | What it is |
|---|---|
| `scripts/build_macos_dmg.py`, `scripts/build_macos_app.py` | macOS `.dmg` and local `.app` launchers |
| `scripts/build_windows.py`, `scripts/desktop_bundle/` | Windows installer (built in CI) |
| `.github/workflows/` | `ci.yml` (tests), `desktop-windows.yml` (installer), `pages.yml` (download page) |

## Checks

| Path | What it is |
|---|---|
| `tests/` | Pipeline, measures, evaluation scripts, desktop (`test_desktop*.py`) |
| `apps/api/tests/` | Service layer and repository tests |
| `scripts/check_project.sh` | Runs the checks below and every Python test |
| `scripts/check_repo_consistency.py`, `scripts/security_scan.py` | Version/path consistency and secret scan |

## Root documents

- `README.md`: user guide (top) and developer guide (bottom)
- `AGENTS.md`, `CLAUDE.md`: instructions for AI agents
- `SCOPE_AND_DELIVERABLES.md`: term paper scope
- `PROJECT_STATUS.md`, `CHANGELOG.md`: status and version history
- `DEVELOPER_SETUP.md`: setting up a development machine
- `KNOWN_LIMITATIONS.md`: limitations

## Not in git

`dist/`, `.local/` (local evaluation audio and caches), `.venv*/`, `models/*`,
`node_modules/`, `__pycache__/`, `.worktrees/`, and AI agent tool folders
(`.agents/`, `.claude/`, `.windsurf/`).

Removed surfaces and where to find them are listed in
[`PROJECT_SOURCE_OF_TRUTH.md`](./PROJECT_SOURCE_OF_TRUTH.md#removed-paths).
