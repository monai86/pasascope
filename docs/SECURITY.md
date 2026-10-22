# Security

PasaScope is a research prototype. Using it with real children's data needs a
separate review by the clinic (consent forms, device security, retention).

## Where data lives

- Everything stays on the therapist's computer: a SQLite database and an audio
  folder in the user's application-data folder
  (`~/Library/Application Support/PasaScope` on macOS, override with
  `PASASCOPE_DESKTOP_HOME`). Nothing is sent to a server.
- Transcription runs on the computer (Whisper). Model files are downloaded on
  first use and every file is checked against its SHA-256
  (`packages/desktop/core/models.py`).
- Updates come from GitHub Releases and are checked against the published
  SHA-256 before they are opened (`packages/desktop/core/updates.py`).
- Backups (`packages/desktop/core/backup.py`) are plain zip files that contain
  recordings and transcripts. They are **not encrypted**; keep them on an
  encrypted disk (FileVault/BitLocker).

## Rules the code keeps

- No session or recording before the caregiver's consent is `granted`;
  withdrawing consent removes that case's recordings.
- Every change writes an audit event with actor, action, target, outcome and
  time, and no transcript text, audio, names or file names.
- Reports pass the report safety check before sign-off; signed reports are
  immutable snapshots with a SHA-256 hash.
- Logs contain no child identifiers, transcript text, audio or file names.
- The clinic speaker model is trained only on that computer's attested
  sessions and is never shared between clinics.

## Repository rules

- Never commit real child data, audio, credentials or `.env` files.
- `python scripts/security_scan.py` scans for secrets (prints file, line and
  category only, never the value). CI runs it on every push.
- `pip-audit -r requirements.txt -r apps/api/requirements.txt` checks
  dependencies; CI treats high/critical findings as blocking.
- Report a problem through GitHub Issues without attaching audio, names or
  anything that identifies a child.
