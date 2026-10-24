# PasaScope (ภาษา-สโคป) service layer

The clinical logic the desktop program (`packages/desktop`) calls in-process.
It was once the backend of the web app; the web server parts (FastAPI routes,
Supabase sign-in, queues, PostgreSQL migrations) were removed on 2026-10-25
and are kept at git tag `web-app-final`.

| Path | What it holds |
|---|---|
| `app/services/` | Transcripts and QA, attestation, features, review cues, report drafting and the report safety check, consent, audio jobs, storage |
| `app/repositories/` | `MockRepository` (in memory, used by tests) and `SqlAlchemyRepository` (the desktop's SQLite file) |
| `app/db/models.py` | Database tables. Keep them compatible with existing desktop databases. |
| `app/schemas/clinical.py` | Pydantic records passed between the services and the desktop |
| `app/core/config.py` | `PASASCOPE_*` settings (storage, ASR strategy, optional recording backup, AI drafting) |
| `app/core/user.py` | `CurrentUser`, the acting therapist |

Rules that live here (see `docs/PROJECT_SOURCE_OF_TRUTH.md`):

- Measures and cues are computed only from an attested transcript; editing or
  replacing a transcript marks its features, cues and report draft `stale`.
- Signed reports keep an immutable snapshot with a SHA-256 hash.
- Consent withdrawal unlinks outputs, deletes stored recordings and blocks
  further work on the case.
- `PASASCOPE_DEBUG_FEATURE_OVERRIDE=false` (the default) keeps failed-QA or
  unattested transcripts out of feature extraction.

Tests, from the repository root:

```bash
PYTHONPATH=apps/api:src pytest apps/api/tests -m "not audio" -q
```

`tests/test_service_rules.py` covers the workflow rules the old HTTP tests
used to check, calling the services the way `DesktopService` does.
