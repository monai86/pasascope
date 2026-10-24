# Development Workflow

Read first: `AGENTS.md`, `docs/PROJECT_SOURCE_OF_TRUTH.md`, `README.md`.
Setup: `DEVELOPER_SETUP.md`.

## Branches

- `main` is the integration branch; a push to `main` runs CI (`ci.yml`) and,
  when `site/` changes, redeploys the download page.
- Use a feature branch for multi-session or risky work. Check
  `git status --short` and the branch before editing.
- Delete merged branches and stale worktrees.

## Where code goes

- Screens and interaction: `packages/desktop/ui`
- Workflow steps, consent and audit: `packages/desktop/core/workflow/<part>.py`
- Clinical logic (measures, cues, reports, safety checks): `apps/api/app/services`
  so there is one implementation
- Audio and language rules: `src/audio_pipeline`, `src/clinical_speech`,
  `packages/features`, `packages/cha`
- Evaluation: a script in `scripts/` that writes to `reports/metrics/`

Changing these boundaries needs an ADR (`docs/adr/`) and updates to
`docs/PROJECT_SOURCE_OF_TRUTH.md`, `README.md` and `AGENTS.md`.

## Verification

```bash
bash scripts/check_project.sh
```

It runs the consistency check, the secret scan, import checks, all Python
tests (Qt tests in their own process). CI adds
the Python 3.11/3.12/3.13 matrix and `pip-audit`.

## Do not commit

`dist/`, `.local/`, `.venv*/`, `models/*`, `node_modules/`, `__pycache__/`,
audio files, databases, credentials, private corpus mirrors.

## Documentation and versions

- Update `README.md` when setup, structure or user-facing behavior changes.
- Update `CHANGELOG.md` for behavior, dependency or release changes.
- Version `v1.8.x`; the version string must match in `README.md`,
  `PROJECT_STATUS.md`, `pyproject.toml` and `CHANGELOG.md`.

## Commits

Conventional Commits (`type(scope): summary`). AI-authored commits carry the
`Co-Authored-By` footer from `AGENTS.md`.

## Clinical and privacy constraints

- Anonymized case codes only.
- No transcript text, audio, identifiers or file names in logs.
- Keep consent, attestation, audit and report sign-off gates.
- Software tests and Gate 1 are not clinical validation.
