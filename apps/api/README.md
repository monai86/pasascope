# PasaScope (ภาษา-สโคป) API and service layer

`app/services/` is the shared service layer the desktop program
(`packages/desktop`) calls in-process: transcripts, features, review cues,
reports, consent and audit rules. The FastAPI app around it (`app/main.py`,
`app/api/`) was the backend of the paused web app, which was removed on
2026-10-23 (git tag `web-app-final`). Its routes stay because `tests/` exercise
the services through them; do not add new web endpoints.

The notes below describe running the API on its own.

Local development defaults to a durable JSON repository at
`.local/pasascope-app-repository.json`. Set
`PASASCOPE_REPOSITORY_MODE=memory` for isolated test/demo runs, or
`PASASCOPE_REPOSITORY_MODE=sql` with
`PASASCOPE_DATABASE_URL` for the SQLAlchemy-backed repository.

Legacy v2 env names remain supported temporarily for backward compatibility.

- `json`: default local usable-prototype persistence; survives API restarts.
- `memory`: isolated tests and intentional demo resets only.
- `sql`: PostgreSQL-ready SQLAlchemy scaffold; not pilot-hardened yet.

Case creation validates bounded de-identified fields server-side and defaults
new records to pending consent. Session workflows remain consent-gated.

Transcript and report creation are retry-safe. If a session already has an
active transcript or editable report draft, creation returns that record.
Intentional transcript replacement requires `replace_existing: true`.

Run locally:

```bash
cd apps/api
PYTHONPATH=.:../..:../../src uvicorn app.main:app --reload --port 8000
```

Run tests:

```bash
cd apps/api
PYTHONPATH=.:../..:../../src pytest -q
```

Repository-root invocation is also supported:

```bash
PYTHONPATH=apps/api:src pytest apps/api/tests -q
```

`PASASCOPE_DEBUG_FEATURE_OVERRIDE=false` is the default and keeps failed-QA
or unattested transcripts blocked from feature extraction. Engineering-only runs
may set it to `true` when they also provide an explicit override reason.
