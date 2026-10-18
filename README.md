# PasaScope (ภาษา-สโคป) — AI-Assisted Thai Pediatric Speech-Language Assessment

Research prototype for extracting speech-language features from Thai language samples, CHAT (`.cha`) transcripts, and audio recordings to support pediatric therapist assessment workflows. Developed as an educational/research decision-support system — **not a diagnostic tool**.

## Project Version Mapping
- **Project version:** `v1.7.4`
- **Therapist product version:** `v1.7.4`

> Start with [`docs/PROJECT_SOURCE_OF_TRUTH.md`](./docs/PROJECT_SOURCE_OF_TRUTH.md).
> It defines which paths are active, legacy, generated, or research-only.
> For the latest verified continuation state and next-work order, read
> [`docs/CURRENT_HANDOFF.md`](./docs/CURRENT_HANDOFF.md).
> For a quick folder map, see [`docs/REPO_STRUCTURE.md`](./docs/REPO_STRUCTURE.md).
> Production architecture freeze artifacts are in
> [`docs/adr/0015-supabase-fastapi-production-boundary.md`](./docs/adr/0015-supabase-fastapi-production-boundary.md),
> [`docs/adr/0016-responsive-web-pwa-only.md`](./docs/adr/0016-responsive-web-pwa-only.md),
> [`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md),
> [`docs/DATA_FLOW_DIAGRAM.md`](./docs/DATA_FLOW_DIAGRAM.md), and
> [`docs/DATA_CLASSIFICATION_INVENTORY.md`](./docs/DATA_CLASSIFICATION_INVENTORY.md).

## Therapist App Interface (v1.7.4)

- **Workflow:** Today → Cases → Session (Intake → Transcript → Findings → Report) → Reports. Each session view names one next step, and a step is ticked only when its work is done.
- **Language:** a TH/EN toggle in the top bar; Thai is the default. Text supplied by the API and organization-administration Settings are English only.
- **Visual system:** a light blue palette split 60 / 30 / 10 with no green. Tokens, components and rules are in [`apps/pasascope-app/DESIGN.md`](./apps/pasascope-app/DESIGN.md); a contract test keeps the palette from drifting.

## ⚠️ Clinical Safety Boundary & Prototype Status

This project is a **research prototype and educational demo**. It supports transcript drafting, descriptive language-sample measures, review cues, and progress reporting only. It does not diagnose ASD and does not replace clinician judgment. The model was trained on English-speaking public corpora and is **not validated for Thai children**.

### Prototype Status & Limitations
- **Persistent Therapist Workflow**: PasaScope persists case, session,
  transcript, QA, attestation, feature, and report records through `apps/api`.
  Local API development defaults to durable JSON storage; browser session
  storage is only a lightweight UI/navigation cache and never stores audio
  bytes.
- **Repository Modes**: `json` is the default usable-prototype mode and
  survives API restarts. `memory` is for isolated tests or intentional demo
  resets. `sql` now includes local pilot plus Phase 1 tenant/RLS foundation,
  but still is not full production hardening.
- **Offline Boundary**: When the API is unreachable, the therapist app shows
  local workspace mode. Safe demo input remains available, but backend-required
  saves, QA, attestation, feature extraction, and finalization cannot report
  success.
- **Secure Upload Gate**: Local pilot mode uses backend-issued
  `local_private` upload intents only after consent is granted. Production
  private audio/video storage still requires managed signed URLs, encryption,
  retention controls, and audit logs.
- **Backend Boundaries**: `apps/api/` is the canonical PasaScope API.
  The experimental audio-to-CHAT implementation remains in
  `src/audio_pipeline/`. `src/therapist_backend/` is retained only as a legacy
  research compatibility API.
- **Human Review Gate**: Generated transcripts require clinician review before preliminary feature outputs or AI-assisted explanation are interpreted.
- **Decision-Support AI Output**: All AI output is strictly designed for screening support (e.g., concern level, review priority, clinician review support) and must never be interpreted as an automated clinical conclusion.
- **Feature-Based ML Review**: PasaScope can persist transparent review
  cues only after transcript attestation and feature extraction. The default
  provider is rule-based, outputs are not diagnostic, browser ML fallback is
  disabled, and cues are not inserted into reports automatically. See
  `docs/ML_DECISION_SUPPORT_MODEL_CARD.md`.
- **Gate 1 Status**: The latest reference-evidence artifact passes the
  preregistered engineering gate and is marked `promoted_candidate`. This does
  not activate diagnosis or establish clinical/Thai validation.

### Clinical Validation Limitations
- The project is not clinically validated and must not be used as a standalone clinical tool.
- The current model and demo workflow have not been validated for Thai children.
- ASR-generated transcripts may be inaccurate for children's speech, noisy audio, overlapping speech, or multilingual speech.
- Public datasets and mock records may not represent all populations, languages, care settings, or communication profiles.
- Model and rule-based outputs require human review by qualified professionals before interpretation.

---


## Maintained Application

### 🩺 Therapist App (`apps/pasascope-app/` + `apps/api/`)

The only active therapist frontend is the Next.js/React/TypeScript app. The
stable path is manual-first: create/open case, create session, upload reviewed
CHA, run QA, attest transcript, extract features, generate AI-assisted
decision-support review, edit/sign off a report, and export only after
therapist sign-off.
Therapists can create a de-identified case from Cases; new cases start with
pending consent and session creation remains locked until the existing consent
verification step is completed.
Signed-off report exports include backend-generated audit metadata: signer,
signed timestamp, report version, and a SHA-256 hash of the signed snapshot.
Edits requested after sign-off create a new draft revision linked to the signed
report, leaving the signed snapshot unchanged for audit.
Transcript edits preserve prior derived records for provenance while marking
existing findings and editable report drafts stale on the backend. Stale
outputs cannot be treated as current, signed off, or exported; the therapist
must regenerate findings and a report from the current transcript version.
LLM/AI report drafting is disabled by default; non-template report providers
require explicit opt-in and record provider/input provenance when requested.
The API also includes an opt-in in-memory rate-limit foundation for local and
pilot hardening; production deployments should replace or front it with managed
edge/API-gateway rate limiting.
CI now runs repository consistency and secret scanning before test/deploy jobs,
with Python and frontend dependency audit steps recorded as production security
gates. Backend deployment hooks are push-to-`main` only and wait for the full
backend matrix, frontend verification, UI audit, E2E, and benchmark lanes.
Repository branch protection remains an owner-configured GitHub control. Known
frontend audit advisories still need remediation before public production release.
Structured request logging uses route templates or sanitized paths so record
IDs, child identifiers, transcript text, storage keys, and raw file names are
not emitted in normal API logs.
CORS allowed origins are configured by environment variable and production
settings fail closed on wildcard or empty origins. Unsafe browser-origin writes
are guarded by an Origin check in the API.
Production runtime settings also fail closed when demo/default database or Redis
URLs, local repositories, local storage, or in-memory queues are configured;
those credentials must be supplied through a managed secret store.
API migration smoke checks now run in verification/CI, and production backup
restore drills must meet the RPO/RTO in `docs/BACKUP_RESTORE_RUNBOOK.md`.
Incident-response stop criteria are documented in
`docs/INCIDENT_RESPONSE_RUNBOOK.md` for cross-tenant exposure, consent bypass,
audit loss, and fabricated ASR output.
Notification/email safety guards require generic operational messages and block
child identifiers, transcript text, audio/storage keys, raw filenames, and
clinical content.
Audit events include actor, action, target, outcome, timestamp, and correlation
ID, with safety validation to keep clinical content out of audit messages.
Production observability settings fail closed unless an approved provider and
critical alert route are configured. Telemetry events are limited to privacy-safe
operational metadata and must not include child identifiers, transcript text,
audio/storage keys, raw filenames, or clinical content.
Privacy deletion-review requests now carry retention/legal-hold metadata and
retain audit/sign-off evidence; legal hold blocks deletion-review completion.
Production also requires an approved secret-store provider and credential
rotation runbook reference; see `docs/SECRET_ROTATION_RUNBOOK.md`.
For the reduced one-day pilot scope, see
`docs/ONE_DAY_PILOT_SCOPE.md` and `docs/ONE_DAY_PILOT_RUNBOOK.md`. The pilot
adds backend organization/care-team guards and local-private upload intents, but
  does not activate production Auth, managed Supabase Storage, legal review, or
  clinical validation.
Phase 1 tenant hardening now adds SQL organization settings, membership and
care-team assignment tables, identity/retention/consent/notification/job-attempt
scaffolds, organization-scoped clinical child records, broader backend route
guards, org-admin membership/care-team assignment endpoints, and PostgreSQL RLS
policy SQL as defense-in-depth. This still requires managed Supabase Auth/RLS
verification before production use.
Backend Supabase Auth verifies the bearer token's signature, issuer and
audience (HS256 or JWKS) and gives every verified user a workspace of their
own, `personal_<user id>`, derived from the token's subject; organization,
role and invitation claims in a token are ignored, and mock headers are ignored
in Supabase mode.
The production boundary is now frozen around Supabase Auth/Postgres/private
Storage plus FastAPI as the authoritative clinical policy layer. Browser clients
may use Supabase Auth and short-lived signed storage URLs only; clinical
workflow reads/writes go through `apps/api`. PasaScope is responsive
web/PWA only, and the removed Vite/Capacitor app must not be recreated.
The `/login` surface is runtime-aware: mock auth mode offers local role and
organization simulation for the mock API, while `supabase` auth mode uses the
browser `@supabase/supabase-js` client for email/password and Google sign-in,
sign-up, recovery email, session restore and auth-state syncing. Every signed-in
account opens its own workspace; there is no organization choice and no
invitation step. Workspace routes send a signed-out visitor to `/login`, and the
API layer sends the Supabase bearer token (no organization header) whenever
`supabase` auth mode is active. Protected audio playback loads through
authenticated blob fetches instead of raw backend file URLs.

The canonical therapist path starts from Home or Cases and opens a persisted
session at `/sessions/{sessionId}`. Session Workspace uses the validated
`?view=intake|transcript|findings|report` query contract and defaults safely to
`intake`. Legacy `/record`, `/results`, `/review-transcript`, `/transcript`, and
`/report-summary` URLs redirect into that workspace when they carry a valid
session identifier; identifier-less legacy entry points redirect to
`/cases?intent=start-session`.

The app has one shell, a chat-first one: a home screen that asks what to do,
four destinations (Home, Cases, Reports, Settings) and one conversation per
session at `/sessions/{sessionId}?view=chat`. It has no language model; what
the app says comes from saved session state. `/` is the home screen, and
`/today` shows the same screen because sign-in links land there. The transcript
editor, findings and report stay full pages reached from the conversation. The
presentation-only `/demo/*` routes and the sample report preview have been
removed; those addresses answer 404. To run it locally:

```bash
cd apps/api
PYTHONPATH=.:../..:../../src uvicorn app.main:app --reload --port 8000

cd ../../apps/pasascope-app
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

See `DESIGN.md` and `docs/adr/0021-chat-first-guided-shell.md`.

Cases and Settings are implemented under feature-owned boundaries. Settings
uses a fail-closed role matrix: therapist-facing sections are available to all
authorized clinicians, while `team` and `audit` are organization-admin only.
Unauthorized section requests resolve safely to `profile`, and admin data
effects are not mounted for therapists.
The maintained frontend is aligned to React 19 / Next.js 16 on Node.js 22 so the
Astryx UI packages can be used without peer-version fallbacks. Astryx agent
docs live under `apps/pasascope-app/.claude/CLAUDE.md`, and the app imports
`@astryxdesign/core/reset.css`, `@astryxdesign/core/astryx.css`, and
`@astryxdesign/theme-neutral/theme.css` from `src/styles/globals.css`.

```bash
cd apps/api
PYTHONPATH=.:../..:../../src uvicorn app.main:app --reload --port 8000

cd ../../apps/pasascope-app
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

Or run the turnkey pilot launcher (starts both backend and web app with health checks):

```bash
bash scripts/launch_pilot.sh
# See docs/PILOT_DEPLOYMENT.md for details
```

Cloudflare Workers staging frontend:

```text
https://lingualens-web.monai-yut.workers.dev
```

Deploy the maintained frontend through OpenNext for Cloudflare:

```bash
cd apps/pasascope-app
npm ci
npm run build:cf
npm run deploy:cf
```

When this frontend talks to the Render staging API, include the worker origin in
`THERAPIST_APP_V2_CORS_ALLOWED_ORIGINS`; otherwise backend-backed auth/API
requests are blocked by browser CORS.

Useful Astryx commands in the therapist app:

```bash
cd apps/pasascope-app
npx astryx build
npx astryx search "dashboard"
npx astryx component Button
```

See `docs/PROFESSOR_DEMO_SCRIPT.md` and
`docs/MVP_VS_EXPERIMENTAL_SCOPE.md` for the walkthrough, scope boundary, and
feature-to-endpoint verification table.

The former `therapist-clinician-app/` Vite/Capacitor surface, removed demo
frontends, and removed benchmark entrypoints are not repository source.
Generated folders from previous local builds may be deleted.

### Assessment v2 (removed)

The assessment-centric `/api/v2` API, its separate PostgreSQL database and
worker, and the `/assessments` screens in the web app have been removed. The
product is the `/api/v1` case and session workflow. The legacy Tkinter GUI still has
its child, consent and assessment panels: it keeps those records itself, in
`~/.pasascope/desktop/records.json` (or the file named by
`PASASCOPE_DESKTOP_RECORDS_PATH`), and asks the API nothing for them.

## Python ML and Audio Research Layer (`packages/` + `src/`)

Research and reference code for model training, evaluation, audio processing,
and artifact generation. New product API routes belong in `apps/api`, not
`src/therapist_backend`.

### Analysis-only transcript boundary

`packages/analysis_contract/` now defines the small reviewed-transcript analysis
boundary. It uses `packages/cha/` for deterministic semantic CHAT subset
round-trip checks and exposes a versioned, dependency-free Thai/mixed tokenizer
profile, descriptive child-only features, explicit QA blockers/limitations, and
SHA-256 provenance. A synchronous execution seam builds the versioned request,
input checksum, profile, and result envelope without returning transcript
content. This package does not own auth, storage, database access, jobs, product
CRUD, or diagnostic interpretation, and it is not yet connected to a product
API or production worker.

### Feature Schema v2 research artifacts

`extract_transcript_features` preserves the legacy v1 mapping and exposes the
v2 research candidate through explicit versioned mappings. V2 adds 8
conversational fields; benchmarks use 21 non-age inputs (13 v1 + 8 v2), while
the local export contains 22 numeric fields when `age_months` is included. The
conversation features use ordered utterance opportunities and return identical
values for file, parsed-object, and normalized-line inputs. Generated v2
Parquet, CSV, and Excel exports are bound by
`data/ml/canonical_features_v2.manifest.json`. Current comparisons are
exploratory, show mixed performance deltas and substantial corpus/protocol
confounding, and do not establish diagnosis, transportability, or Thai clinical
validity.

### CLAN-Derived Metrics

The TalkBank/CHILDES reference pipeline can run CLAN batch jobs and parse
completed KIDEVAL output into `data/reference/english_child_clan_features.csv`.
These rows are kept separate from the Python-derived reference features and are
descriptive research artifacts only. The Reference Comparison API can expose
matched CLAN-Derived Metrics in a separate `clan_metric_comparisons` section;
the therapist Transcript tab displays that section separately when backend
Reference Comparison is configured and matched CLAN metrics are available.
The therapist API also exposes `GET /api/sessions/{session_id}/qa` so the
Transcript tab can use backend CHAT/CLAN readiness checks before unlocking
Reference Comparison; mock mode remains a lightweight local QA preview and does
not pretend to validate CLAN readiness.

### Desktop App (`packages/desktop/`) — term paper deliverable

`./run_gui.sh` (or `pasascope`) opens a PySide6 program that runs the clinical
workflow on one computer with no server: case and consent → session → record
or import audio (on-device Whisper, progress and cancel) → correct the draft
against the waveform and attest → features and review cues → Thai report,
sign-off, PDF/HTML/Markdown/CHAT export. It calls the `apps/api` service layer
in-process over SQLite in the user's application-data folder
(`~/Library/Application Support/PasaScope` on macOS; override with
`PASASCOPE_DESKTOP_HOME`). Transcription mode (Thai model, or the faster
multilingual model) is under ตั้งค่า → โหมดถอดเสียง. Tests:
`tests/test_desktop_service.py`, `tests/test_desktop_ui.py`.

### Terminal TUI and Legacy Desktop GUI (`packages/tui/`, `packages/gui/`)

The Tkinter GUI below is retained as `./run_gui.sh --legacy` and is no longer
developed.

The terminal TUI (`packages/tui/`) and desktop companion GUI (`packages/gui/`) provide clinician
companion workflows. The desktop GUI features a **Therapist 5-Step Guided Workflow** (`Open Case` ➔ `Add Session` ➔ `Ingest Material` ➔ `Review Transcript` ➔ `Progress Report`) with interactive step progress badges, a dynamic Next Action Ribbon, collapsible technical diagnostic disclosures, **Live Microphone Recording** with a real-time VU meter, and a **Deep Thai Clinical Language Sample Analyzer (Thai LSA Engine)** powered by `pythainlp`.

In live mode (`mock_mode=False`), all client operations communicate strictly
with the backend REST API (`apps/api`) or fail closed with structured, sanitized exceptions
(`PasaScopeApiError`). Live mode never mutates local mock state, and unsupported operations fail
explicitly without fabricating local success. Explicit local mock mode (`mock_mode=True`) is
reserved for offline demonstrations and research prototyping.


The reference pipeline also writes
`data/reference/english_child_reference_coverage.csv` and
`docs/REFERENCE_COHORT_COVERAGE.md` to summarize which age/task/group cells are
ready for cautious descriptive comparison and which cells remain low-count. The
current reference snapshot includes 1,961 Python-derived feature rows and 1,961
matched CLAN-Derived Metric rows across the Phase 1 and Phase 2 transcript
intake corpora. Reference feature rows include `age_months_source` and
`age_months_source_detail` so CHAT header ages and official-path fallbacks for
NewEngland/Rescorla remain auditable.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Pipeline (run in order)

```bash
python src/data_loader.py                   # build combined_features.csv + longitudinal_features.csv
python src/eda.py                           # summary stats + plots → reports/figures/
python src/progress_tracking.py            # longitudinal analysis (Rollins + Flusberg)
python -m packages.ml.train_model --features-csv data/combined_features.csv
```

### Key ML Results

Current maintained ML reporting is the reference-evidence Gate 1 pipeline:

| Metric | Value |
|-------|-------|
| Sensitivity | `0.8862` |
| Sensitivity lower 95% CI | `0.8091` |
| Specificity | `0.6124` |
| ECE | `0.0332` |
| Abstention | `0.3166` |

These are engineering gate metrics for therapist review support only. They are
not clinical validation and must not be presented as diagnosis.

---

## Data Sources (TalkBank / ASDBank)

### Cross-sectional (122 children)

| Corpus | Groups | Folder |
|--------|--------|--------|
| Eigsti | ASD 16 / DD 16 / TD 16 | `data/Eigsti/` |
| Nadig | ASD 13 / TD 25 | `data/Nadig/` |
| NYU-Emerson | ASD 30 | `data/NYU-Emerson/` |
| Flusberg | ASD 6 (session 1) | `data/Flusberg/` |

### Longitudinal (87 sessions, 12 children)

| Corpus | Children | Sessions |
|--------|----------|----------|
| Rollins | 5 | 21 |
| Flusberg | 6 | 64 |
| QuigleyMcNally | 2 | 2 |

---

## Features Extracted per `.cha` (14 features)

- **Productivity:** `total_utterances`, `total_words`
- **Complexity:** `mlu` (morphemes), `mluw` (words)
- **Lexical diversity:** `ttr` (type-token ratio)
- **ASD markers:** `unintelligible_count/ratio` (`xxx`/`yyy`), `zero_vocalization_count` (`0 .`), `nonverbal_vocalization_count`, `echolalia_count/ratio`, `pronoun_reversal_count`
- **Pragmatic:** `question_ratio`

---

## Audio Pipeline

End-to-end `.wav` → `.cha` pipeline using Whisper ASR + speaker diarization.

```bash
python -m src.audio_pipeline.pipeline recording.wav \
    --model small --strategy thai --age-months 48
# → writes recording.cha next to recording.wav
```

The therapist web app uses the same pipeline for uploaded recordings when
on-device transcription is enabled:

```bash
PASASCOPE_ASR_LOCAL_WHISPER_ENABLED=true bash scripts/start_local.sh
```

Recordings stay on the machine running the API. With the flag off, the app
reports that transcription is unavailable and offers paste or `.cha` import; it
never substitutes synthetic text. `PASASCOPE_ASR_WHISPER_MODEL_SIZE` (default
`medium`) and `PASASCOPE_ASR_LANGUAGE_STRATEGY` tune it. The default,
`thai_specialized`, sends a recording the multilingual model hears as Thai to
Thonburian Whisper, a Thai fine-tuned model, and any other recording to the
multilingual model; the draft records which model wrote it. The Thai model has
to be converted once with `bash scripts/convert_thai_whisper.sh` (see
`models/README.md`); until then on-device transcription reports itself
unavailable, and `PASASCOPE_ASR_LANGUAGE_STRATEGY=auto` uses the multilingual
model only. `thai` or `english` forces one language.

**Evaluating it on Thai recordings:** follow
[`data/evaluation/README.md`](./data/evaluation/README.md), then run
`python scripts/evaluate_thai_asr.py` for word/character error rates, speaker
attribution, and feature drift, and
`python scripts/report_transcript_review_time.py` for review time.

**Diarization backends:**
- `EmbeddingDiarizer` (default) — ECAPA-TDNN embeddings, no HF token needed
- `PyannoteDiarizer` (optional) — SOTA, requires `HF_TOKEN`

---

## Research Support Scripts

```bash
python scripts/paper_scout.py --tag speech --tag audio --save   # ASD/AI paper discovery
python scripts/build_zotero_import.py                           # Zotero RIS export
```

See `docs/literature/PAPER_SCOUT.md` for full workflow. Reports saved to `docs/literature/scout_reports/`.

### Build reference-evidence artifacts

Reference evidence is English-only, descriptive, and opt-in. It does not
produce probabilities, predicted classes, rankings, or diagnosis.

```bash
export ML_REFERENCE_PSEUDONYMIZATION_KEY='replace-with-32-or-more-secret-bytes'
python scripts/build_ml_reference_evidence.py \
  --combined data/combined_features.csv \
  --curated data/curated_group_features.csv \
  --output-dir artifacts/reference_evidence/candidate-v1 \
  --artifact-version candidate-v1 \
  --feature-parity-passed
```

Artifact promotion is manual and approval-recorded. See
[`docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md`](./docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md).

---

## Tests

```bash
PYTHONPATH=apps/api:src pytest -m "not audio" -q # core + active API tests
pytest tests/test_feature_schema.py -q          # 14-feature schema alignment
pytest tests/test_transcript_reviewer.py -q     # CHAT transcript QA
pytest tests/test_clinical_workflow.py -q       # therapist app mock backend
pytest tests/test_clinical_pilot_backend_contract.py -q
cd apps/pasascope-app && npx playwright install chromium && npm run e2e:smoke # guided session browser smoke test
PLAYWRIGHT_BACKEND_PORT=8001 PLAYWRIGHT_FRONTEND_PORT=3101 npm run e2e:smoke # use alternate local ports if 8000/3100 are already in use
```

Focused local maintained-project verification (not the complete CI candidate):

```bash
bash scripts/check_project.sh
```

It omits dependency audits, the Python version matrix, frontend lint/typecheck,
the UI audit, full therapist and demo Playwright suites, and the transcript
benchmark baseline gate.

---

## Project Structure

```
asd-project/
├── apps/
│   ├── pasascope-app/          # 🩺 Active Next.js therapist frontend
│   └── api/                       # Therapist workflow FastAPI
├── src/
│   ├── audio_pipeline/            # .wav → .cha (Whisper + diarization + CHAT)
│   ├── clinical_workflow/         # Legacy/research workflow compatibility
│   ├── therapist_backend/         # Legacy research API compatibility
│   ├── data_loader.py             # CHAT → features CSV
│   ├── feature_schema.py          # Shared v1 and conversation-v2 schemas
│   ├── progress_tracking.py       # Longitudinal trends + composite score
│   ├── transcript_reviewer.py     # Rule-based CHAT QA
│   ├── therapist_report.py        # Progress report generator
│   ├── speech_therapist_assistant.py  # Therapist interpretation layer
│   └── evaluate_asr.py            # WER evaluation
├── scripts/
│   ├── paper_scout.py
│   └── build_zotero_import.py
├── tests/                         # pytest test suite
├── data/                          # Raw .cha corpora + generated CSVs
├── artifacts/                     # screening_model.joblib, model_card.json, feature_schema.json
├── reports/
│   ├── figures/                   # Saved plots
│   ├── metrics/                   # Current reference/progress evaluation outputs
│   └── progress_reports/          # Sample therapist reports
├── docs/                          # Documentation
│   ├── DEPLOYMENT.md              # Cloudflare Pages deploy guide
│   ├── REFERENCES.md              # Bibliography (37+ papers)
│   ├── THAI_VALIDATION_READINESS_TH.md
│   ├── PRESENTER_GUIDE_TH.md
│   └── literature/                # Paper scout outputs, Zotero imports
├── .agents/skills/                # Project-level AI agent skills
├── CHANGELOG.md
├── CONTEXT.md                     # Canonical glossary
├── PROJECT_STATUS.md              # Current maintained status
└── requirements.txt
```

---

## Deployment

See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) for the current therapist-app
deployment path and maintained ML artifact workflow.

---

## Key Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/REFERENCES.md`](./docs/REFERENCES.md) | Bibliography 37+ papers |
| [`docs/THAI_VALIDATION_READINESS_TH.md`](./docs/THAI_VALIDATION_READINESS_TH.md) | Thai validation readiness and governance boundary |
| [`docs/PRESENTER_GUIDE_TH.md`](./docs/PRESENTER_GUIDE_TH.md) | คู่มือนำเสนอ 3-5 นาที |
| [`CONTEXT.md`](./CONTEXT.md) | Shared glossary |
| [`docs/PROJECT_SOURCE_OF_TRUTH.md`](./docs/PROJECT_SOURCE_OF_TRUTH.md) | Active/legacy/generated architecture map |
| [`docs/CURRENT_HANDOFF.md`](./docs/CURRENT_HANDOFF.md) | Latest verified state, deferred work, and continuation brief |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history |
| [`SCOPE_AND_DELIVERABLES.md`](./SCOPE_AND_DELIVERABLES.md) | What the term paper presents and what is out of scope |
| [`docs/TERM_PAPER_MAPPING.md`](./docs/TERM_PAPER_MAPPING.md) | Term-paper sections mapped to system parts and evidence |
| [`docs/ML_DECISION_SUPPORT_MODEL_CARD.md`](./docs/ML_DECISION_SUPPORT_MODEL_CARD.md) | ML and reference-evidence scope, gates, and limitations |
| [`docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md`](./docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md) | Artifact approval, promotion, rollback, and incident runbook |
