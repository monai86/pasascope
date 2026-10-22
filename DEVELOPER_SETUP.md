# PasaScope Developer Setup

How to run, test and build the PasaScope desktop program from source.

> PasaScope is a research prototype. It is **not a diagnostic tool** and is
> **not clinically validated** for Thai children. Never put real child names or
> identifiers into fixtures, logs or committed data.

## Prerequisites

- Python 3.11–3.13 (3.12 recommended)
- macOS on Apple silicon or Windows 10/11
- For CLAN comparisons only: UnixCLAN (`docs/CLAN_BATCH_RUNBOOK.md`)

## 1. Install

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt            # pipeline, ML, audio
pip install -r apps/api/requirements.txt   # service layer
pip install -r requirements-desktop.txt    # PySide6, pytest-qt
```

`run_gui.sh` and `scripts/check_project.sh` look for `.venv312` first, then
`.venv`.

## 2. Run the desktop program

```bash
./run_gui.sh          # your own data
./run_gui.sh --demo   # demonstration data
```

- Data folder: `~/Library/Application Support/PasaScope` on macOS (override
  with `PASASCOPE_DESKTOP_HOME`). Demo data: `python scripts/seed_desktop_demo.py`
  fills `~/Library/Application Support/PasaScope Demo`.
- Whisper models download on first use. To use a local Thai model instead,
  convert it with `bash scripts/convert_thai_whisper.sh` (see `models/README.md`).
- Transcription mode (accurate Thai model or fast multilingual model) is under
  ตั้งค่า → โหมดถอดเสียง.

## 3. Test

```bash
bash scripts/check_project.sh                               # everything below
PYTHONPATH=apps/api:src pytest tests/test_desktop*.py -q    # desktop (Qt)
PYTHONPATH=apps/api:src pytest tests -m "not audio" --ignore-glob="tests/test_desktop*.py" -q
PYTHONPATH=apps/api:src pytest apps/api/tests -m "not audio" -q
PYTHONPATH=apps/api:src pytest -m audio                     # needs faster-whisper, speechbrain, librosa
```

On macOS keep the Qt tests in their own pytest process.

## 4. Build

- macOS `.dmg`: `python scripts/build_macos_dmg.py` (writes `dist/`)
- Local launchers for this machine only: `python scripts/build_macos_app.py`
- Windows installer: built by `.github/workflows/desktop-windows.yml`
  (`scripts/build_windows.py`)
- Releasing: `docs/DESKTOP_RELEASE.md` (needs the project owner's approval)

## 5. Reproduce the evaluation

See the table in `README.md` ("Evaluation") and
`reports/metrics/EVALUATION_SUMMARY.md`. Evaluation audio is not in git; follow
`data/evaluation/README.md` and `docs/TALKBANK_DOWNLOAD_RUNBOOK.md`.
