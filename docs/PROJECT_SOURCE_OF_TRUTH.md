# Project Source of Truth

เอกสารนี้เป็นจุดอ้างอิงหลักสำหรับคนและ AI agents ทุกตัวที่ทำงานใน repository
นี้ ไม่ว่าจะมาจาก Codex, Antigravity, Claude หรือเครื่องมืออื่น

## สถานะปัจจุบัน

- ชื่อโครงการ: **PasaScope (ภาษา-สโคป)** (เดิม LinguaLens)
- รุ่นโครงการ: `v1.7.7`
- active user-facing surfaces และ API ใช้ version `v1.7.7`
- branch หลัก: `main`
- ตัวหลักของ term paper (ตั้งแต่ 2026-10-16): **โปรแกรมเดสก์ท็อป** `packages/desktop/`
  (PySide6, เปิดด้วย `./run_gui.sh` หรือคำสั่ง `pasascope`) รัน service layer ของ
  `apps/api` ในโปรแกรมเดียวบน SQLite ในเครื่อง ไม่มี server; web app พักการพัฒนา
  ดู `SCOPE_AND_DELIVERABLES.md`
- Therapist frontend (web, พักการพัฒนา): `apps/pasascope-app/`
- Therapist frontend runtime: Next.js `^16.3.8` / React 19 / Node.js `22.x`
- Therapist workflow API หลัก: `apps/api/`
- ML/audio/research libraries: `packages/` และ `src/`
- Analysis-only transcript contract: `packages/analysis_contract/` และ
  deterministic CHAT subset utilities ใน `packages/cha/`
- ระบบเป็น research/education prototype และ clinical review support เท่านั้น
- ระบบไม่วินิจฉัย ASD และยังไม่มี Thai clinical validation

## Canonical runtime surfaces

| Surface | Canonical path | สถานะ |
|---|---|---|
| Desktop app (term paper deliverable) | `packages/desktop/` | Active |
| Therapist web app | `apps/pasascope-app/` | Paused |
| Therapist workflow API / shared service layer | `apps/api/` | Active (service layer used in-process by the desktop app) |
| Legacy Tkinter GUI | `packages/gui/` (`./run_gui.sh --legacy`) | Retained, not developed |
| Research ML/audio | `packages/`, `src/`, `scripts/` | Active research tooling |
| Analysis-only transcript boundary | `packages/analysis_contract/`, `packages/cha/` | Active research contract; not a product API |

`apps/api` เป็น backend ที่ frontend หลักเรียกใช้ผ่าน `/api/v1`.

Session Workspace ใช้ canonical route เดียวคือ `/sessions/{sessionId}` พร้อม
validated `?view=intake|transcript|findings|report`; ค่า query ที่หายหรือไม่ถูกต้อง
ต้อง fallback เป็น `intake`. Legacy session routes เป็น compatibility redirects
เท่านั้น และ route ที่ไม่มี session identifier ต้องไป
`/cases?intent=start-session`. Report library ต้องเปิด editor ผ่าน Session
Workspace ไม่สร้าง report editor route แยกอีกชุด.

Presentation-only `/demo/*` routes และ `/reports/preview` ถูกถอดออกแล้ว ที่อยู่
เหล่านั้นต้องตอบ 404 (ตรวจใน `e2e/route-gates.spec.ts`) และห้ามเพิ่มหน้าที่แสดง
ข้อมูลตัวอย่างกลับเข้ามาใน app หลัก.

Chat shell เป็น shell เดียวของ app (ADR
`docs/adr/0021-chat-first-guided-shell.md`); shell แบบ workbench เดิม (sidebar,
topbar, bottom nav, หน้า Today, Dashboard) และ flag `NEXT_PUBLIC_CHAT_SHELL`
ถูกถอดออกแล้ว. `/` เป็นหน้าหลัก และ `/today` แสดงหน้าเดียวกันเพราะลิงก์ sign-in
ยังพามาที่นั่น; `/dashboard` redirect ไป `/`.
Navigation มี 4 ปลายทางคือ
Home, Cases, Reports, Settings (ไม่มี bottom nav; ลำดับถูกตรวจใน
`src/__tests__/chat-shell.test.tsx`), และ Session Workspace เพิ่ม route view
`?view=chat` เป็นบทสนทนาของเซสชัน โดย `?view=intake` เปิดบทสนทนาเดียวกัน ส่วน
`transcript|findings|report` ยังเป็นหน้าเต็มเดิม. บทสนทนาเป็นภาพฉายของสถานะเซสชันใน
backend ไม่ใช่ log ข้อความที่เก็บไว้ และไม่มี language model; consent ต้องได้รับ
ก่อนสร้างเซสชันเสมอ. ข้อความที่พิมพ์ในหน้าหลักของ chat shell ถูกจับคู่กับรายการ
หัวข้อตายตัว (ADR `docs/adr/0022-fixed-topic-answers-on-chat-home.md`): ตอบ
คำถาม เปิดหน้า หรือเริ่ม guided start ได้ แต่ห้ามเปลี่ยน record ใด ๆ จากข้อความที่
พิมพ์โดยไม่มีการกดปุ่มยืนยัน และห้ามเก็บ ส่งไป API หรือ log ข้อความนั้น. ข้อความที่
พิมพ์ในบทสนทนาของเซสชันยังเป็น session note เท่านั้น.

Cases และ Settings ใช้ feature-owned components/hooks/services โดย compatibility
components เดิมเป็น thin entry points เท่านั้น. Settings section matrix ต้อง
fail closed: `profile`, `organization`, `credentials`, `accessibility`, `privacy`
เป็น clinician sections; `team` และ `audit` เป็น organization-admin only และ
ห้าม mount admin data effects สำหรับ therapist.

`src/therapist_backend` เป็น legacy research/pilot API ที่ยังเก็บไว้เพราะชุด
research tests และ workflow เดิมบางส่วนยังใช้มัน ห้ามเพิ่ม endpoint ผลิตภัณฑ์
ใหม่ที่นี่ เว้นแต่งานนั้นระบุชัดว่าแก้ legacy compatibility.

`src/clinical_workflow` เป็น legacy/research domain implementation และไม่ใช่
persistence layer หลักของ pasascope.

## Removed and generated paths

- `therapist-clinician-app/` รุ่น Vite/Capacitor ถูกถอดออกจาก Git แล้ว
- `public-screening/` และ `presentation-dashboard/` ถูกถอดออกจาก working tree
  เพื่อให้ repository เหลือเฉพาะ maintained surfaces
- legacy benchmark pipeline (`src/classifier.py`, `src/deep_learning.py`,
  `src/fairness_metrics.py`, `scripts/compute_fairness_metrics.py`) ถูกถอดออก
  จาก working tree แล้ว
- `.next/`, `dist/`, `.local/`, `node_modules/`, `*.tsbuildinfo` เป็น generated
  หรือ local runtime files และต้องไม่ commit
- ถ้าโฟลเดอร์ legacy ปรากฏในเครื่องจาก build เก่า ให้ลบได้โดยไม่กระทบ source
- เอกสาร implementation plans/specs เก่าถูกเก็บใน Git history ไม่อยู่ใน
  working tree ปัจจุบัน

## Backend source-of-truth rules

1. Backend records เป็น source of truth เมื่อมี case/session/transcript/report ID
2. `sessionStorage` เป็น UI cache หรือ local fallback เท่านั้น
3. JSON repository เป็น default สำหรับ local prototype
4. Memory repository ใช้เฉพาะ tests และ intentional reset
5. SQL repository มี transactional slices สำหรับ case/session/transcript/report,
   privacy, feature/AI/ML review, membership, care-team assignment และ Phase 1
   tenant/RLS schema foundation แล้ว แต่ยังไม่ถือว่า production-hardened จนกว่า
   จะ verify กับ managed Postgres/Supabase และ production auth จริง
6. Browser ห้ามสร้าง ML result หรือ report-final state แทน backend
7. Signed-off reports ต้องมี backend-generated signed snapshot, SHA-256 report
   hash, signer, version และ export timestamp เพื่อ audit/export ย้อนหลังได้;
   การแก้ report หลัง sign-off ต้องสร้าง draft revision ใหม่ที่อ้างถึง report
   เดิม ไม่แก้ signed snapshot เดิมแบบเงียบ
8. AI report drafting ต้อง default off และเปิดด้วย explicit environment หรือ
   organization opt-in เท่านั้น; ทุก AI draft request ต้องเก็บ provider/model/
   input-hash provenance และยังต้อง editable/rejectable ก่อน sign-off
9. เมื่อ transcript เปลี่ยน backend ต้องคง derived records เดิมไว้เพื่อ audit
   แต่ทำเครื่องหมาย findings และ report draft ที่มีอยู่เป็น `stale`; stale
   findings ห้ามใช้เป็น current input และ stale report ห้ามแก้, sign off หรือ
   export จนกว่าจะ regenerate จาก transcript version ปัจจุบัน ส่วน signed
   snapshot เดิมต้อง immutable
10. API rate limiting ต้องเปิดได้ด้วย server-side configuration และ 429 response
   ต้องเป็นข้อความทั่วไป ไม่มี child identifier, transcript, audio key หรือ
   clinical content
11. CI ต้องรัน repository consistency และ secret scan ก่อน test/deploy; Python
    และ frontend dependency audits เป็น blocking gates ที่ต้องไม่มี unresolved
    critical/high findings
12. Structured request logs ต้องใช้ route template หรือ sanitized path เท่านั้น
    และต้องไม่บันทึก child identifier, transcript text, audio content, storage key,
    raw file name หรือ raw URL ที่มี clinical identifiers
13. CORS origins ต้องมาจาก server-side configuration เท่านั้น; production ห้าม
    ใช้ wildcard/empty origins และ unsafe HTTP methods ต้องมี Origin guard ที่
    reject untrusted origins ด้วย generic 403
14. Production runtime (`PASASCOPE_MOCK_MODE=false`) ต้อง fail-closed ถ้า
    ยังใช้ repository/storage/job queue แบบ local/demo หรือใช้ database/Redis URL
    default; secrets ต้องมาจาก managed secret store และหมุน credentials ได้
15. Production database ต้องมี backup/PITR และ restore drill ตาม
    `docs/BACKUP_RESTORE_RUNBOOK.md`; CI/local verification ต้องมี API migration
    smoke check ที่สร้างฐานใหม่และ migrate ถึง Alembic head
16. Incident response ต้องหยุด rollout ทันทีเมื่อพบ cross-tenant exposure,
    consent bypass, audit loss หรือ fabricated ASR output และต้องทำตาม
    `docs/INCIDENT_RESPONSE_RUNBOOK.md` โดยไม่คัดลอก clinical content ลง
    operational tools
16a. In-app notifications และ email ต้องเป็น generic operational messages เท่านั้น
    และต้องไม่ใส่ child identifiers, transcript text, audio content, storage keys,
    raw filenames, report excerpts หรือ clinical content
17. Audit events ต้องมี actor, action, target, outcome, timestamp และ correlation
    ID และต้องไม่บันทึก child identifiers, transcript text, audio content, storage
    keys, raw filenames, report excerpts หรือ clinical content
18. Production observability ต้องเปิดใช้งานด้วย approved provider เช่น Sentry,
    CloudWatch หรือ OTLP และต้องมี critical alert route; telemetry tags/details
    ต้องเป็น operational metadata เท่านั้น และห้ามมี child identifiers, transcript
    text, audio content, storage keys, raw filenames, report excerpts หรือ
    clinical content
19. Privacy operations ต้องบันทึก retention policy, legal hold, deletion-review
    state และ evidence-retention summary; deletion review ห้าม complete ระหว่าง
    legal hold และห้ามลบ audit/sign-off evidence อัตโนมัติ
20. Production secrets ต้องมาจาก managed secret store เท่านั้น และต้องกำหนด
    credential rotation runbook; ห้ามใช้ local env/demo defaults เป็น production
    secret source
21. Production architecture freeze artifacts are active controls:
    `docs/adr/0015-supabase-fastapi-production-boundary.md`,
    `docs/adr/0016-responsive-web-pwa-only.md`, `docs/THREAT_MODEL.md`,
    `docs/DATA_FLOW_DIAGRAM.md`, and
    `docs/DATA_CLASSIFICATION_INVENTORY.md`.
22. Browser/PWA clients may use Supabase Auth and FastAPI-issued short-lived
    signed storage URLs only; all clinical reads/writes and workflow transitions
    must pass through `apps/api`.
23. pasascope is responsive web/PWA only. Do not recreate the removed
    Vite/Capacitor app or add a native shell without a new accepted ADR.
24. One-day production-like pilot scope is frozen in
    `docs/ONE_DAY_PILOT_SCOPE.md` and operationalized by
    `docs/ONE_DAY_PILOT_RUNBOOK.md`. This pilot adds local/SQL tenant
    scaffolding, backend org/care-team guards, and local-private upload intents,
    but it is not full production readiness.
25. Non-mock runtime must use non-mock auth mode. `PASASCOPE_AUTH_MODE=mock`
    is allowed only for local pilot/demo mode; production must use a
    production-capable auth mode such as Supabase. The local Supabase Auth
    scaffold and required JWT claim contract are documented in
    `docs/SUPABASE_AUTH_CONTRACT.md`.
26. Phase 1 tenant isolation foundation now includes organization settings,
    memberships, care-team assignment, identity profile, regional retention,
    consent, notification, job-attempt SQL tables, organization-scoped clinical
    child records, backend organization-admin membership and case care-team
    assignment endpoints, application-level guards on clinical routes, and a
    PostgreSQL RLS migration as defense-in-depth. This is implementation
    foundation only; production readiness still requires Supabase Auth/RLS
    verification, invitation/MFA frontend flows, managed private Storage, and
    security/legal rollout evidence. Durable asynchronous execution is required
    only if measured workload cannot be handled synchronously or by the existing
    database-backed job model with one worker.
27. The organization/invitation lifecycle (org-admin invitations, membership
    revocation, break-glass access) has been removed from the API and the web
    app. Every verified Supabase user has one personal workspace,
    `personal_<user id>`, derived from the token subject; the web sign-in has no
    organization selection, invitation step or mandatory MFA screen, and sends
    no organization header. Two-step verification (TOTP) is opt-in per account
    and enforced by the API for that account's `aal1` sessions, and an account
    holder can delete their account with everything in it
    (`DELETE /api/v1/account`); both need the Supabase service role key (ADR
    `docs/adr/0023-opt-in-two-step-verification-and-self-service-deletion.md`).
28. Current Phase 1 external blockers and exact next actions are tracked in
    `docs/PHASE1_EXTERNAL_BLOCKERS.md`.
29. Research evaluation helpers under `apps/api/app/api/v1/routes/evaluation.py`
    are local/mock-only tooling. Production-like runtime must reject them
    fail-closed; they are not part of the first clinic SaaS workflow surface.
30. Provider-discovery routes in the maintained API are authenticated surfaces,
    not public capability manifests. Production-like runtime must require a
    valid session before returning provider metadata.
31. The analysis-only transcript boundary provides deterministic semantic CHAT
    round-trip checks, a versioned dependency-free Thai/mixed tokenizer profile,
    descriptive child-only feature definitions, structured blockers/limitations,
    explicit checksums/provenance, and a synchronous execution seam. It has no
    FastAPI, database, auth, storage, queue, or product-workflow ownership and is
    not wired into a product API or production jobs yet.

32. ASR ใน v1 workflow: provider ที่ใช้ชื่อ engine ต้องรัน engine นั้นจริง ห้าม
    register provider ที่ติดป้ายข้อความจาก client เป็นผล ASR. `local_whisper`
    เป็น opt-in (`PASASCOPE_ASR_LOCAL_WHISPER_ENABLED`) รันบนเครื่อง API เท่านั้น
    และต้องปฏิเสธ strategy ที่ส่งเสียงออกนอกเครื่อง. เมื่อถอดเสียงไม่สำเร็จต้องรายงาน
    failed โดยไม่มีข้อความทดแทน ทั้งใน API และใน offline adapter ของ GUI/TUI.
    Web app ต้องไม่เลือก mock provider แทนผู้ใช้
33. ค่า feature ภาษาไทย (MLU-w, TTR, echolalia cue, pronoun cue) ต้องมาจากกฎชุด
    เดียวใน `src/clinical_speech/thai_lsa.py` ทั้งใน `apps/api` และ GUI; ห้ามมีสูตร
    สำรองหรือค่าคงที่แทนค่าที่คำนวณไม่ได้ ให้ส่งเป็นค่าว่างแทน. สถานะของ guideline
    link ต้องเป็นคำบรรยายสิ่งที่นับได้ ไม่ใช่คำตัดสินเทียบเกณฑ์
34. โปรแกรมเดสก์ท็อปเรียก service ใน `apps/api/app/services` ตรง ๆ ผ่าน
    `packages/desktop/core/service.py` และต้องคงการตรวจความยินยอม audit event และ
    การตรวจความปลอดภัยของรายงานแบบเดียวกับ route ของ API; ห้ามมีสูตรวิเคราะห์ของตัวเอง.
    session ใหม่และการบันทึกเสียงต้องมีความยินยอมสถานะ `granted`. รายงานบนเดสก์ท็อปใช้
    provider `template_th` และ export PDF ด้วย Qt (ฟอนต์ไทยของระบบ)
35. โมเดลแยกเสียงเด็ก/ผู้ใหญ่ประจำคลินิก (`src/audio_pipeline/clinic_speaker_model.py`)
    เรียนบนเครื่องจาก transcript ที่รับรองแล้ว ร่างโดย Whisper และมีไฟล์เสียงในเครื่อง
    ของเด็กที่ความยินยอมยังเป็น `granted` เท่านั้น; ต้องมีอย่างน้อย 4 session จากเด็ก 2 คน
    และใช้แทนโมเดล USC ก็ต่อเมื่อ balanced accuracy แบบกันเด็กทีละคนสูงกว่าอย่างน้อย 2 จุด.
    ห้ามแจกโมเดลที่เทรนแล้วข้ามคลินิก. การเทรน เปิด/ปิด และล้าง ต้องมี audit event
    และป้าย ? ตามช่วงอายุยังมีผลเสมอ
36. ร่างภาษาอังกฤษตัดประโยคด้วยโมเดล logistic regression ที่อธิบายได้
    (`src/audio_pipeline/utterance_boundaries.py`, ไฟล์ `src/audio_pipeline/models/utterance_boundaries_en.json`
    ต้องรวมไปกับแอปตอน build) ทุกประโยคที่โมเดลเริ่มใหม่ต้องเก็บเหตุผลให้นักบำบัดอ่าน;
    ภาษาไทยยังใช้กฎช่วงหยุด 0.6 วินาที และ `PASASCOPE_UTTERANCE_BOUNDARIES=rule` ปิดโมเดลได้
36a. รายงาน session ของแอป desktop เขียนได้ทั้งไทย (`template_th`) และอังกฤษ (`template_clinic_en`)
    ด้วยถ้อยคำคงที่ หัวข้อเดียวกัน; PDF และตัวอย่างก่อนพิมพ์วาดด้วย `paint_report` ตัวเดียว
    ตามรูปแบบใน `docs/REPORT_LAYOUT.md`; ฟอนต์ TH Sarabun New (GPL + font exception) และ Sarabun (OFL) ใน `packages/desktop/ui/assets/fonts/`
    และโลโก้ `logo.png` ต้องรวมไปกับแอปตอน build พร้อมไฟล์ไลเซนส์ของฟอนต์
36b. Feature schema `features-basic-v3` เพิ่มตัวชี้วัดการผลัดกันพูด (`packages/features/turn_taking.py`);
    หน้าตัวชี้วัดและรายงานแสดงเฉพาะตัวหลักใน `labels.CORE_FEATURES` ตามหลักฐานใน `docs/FEATURE_GUIDE.md`
    และทุกตัวชี้วัดต้องมีคำอธิบายใน `packages/desktop/ui/feature_guide.py` (มีเทสต์บังคับ)
36c. แอป desktop แจกเป็น `.dmg` จาก `scripts/build_macos_dmg.py` และอัปเดตจาก GitHub Releases
    ตาม `docs/DESKTOP_RELEASE.md`; โมเดลเสียงดาวน์โหลดตอนใช้ครั้งแรกและตรวจ SHA-256 ทุกไฟล์
    (`packages/desktop/core/models.py`); การสร้าง release ต้องได้รับอนุญาตจากเจ้าของโครงการ
36d. แอป desktop มีธีมสว่างและมืด (`packages/desktop/ui/theme.py`, ชุดสี `LIGHT`/`DARK` ชื่อเดียวกัน)
    ค่าเริ่มต้นตามเครื่อง เลือกเองได้ที่ ตั้งค่า → ธีม (เก็บใน QSettings `appearance/theme`);
    widget ต้องอ่านสีจาก `theme.<NAME>` ตอนสร้างหรือวาด ห้ามคัดลอกสีไปเป็นค่าคงที่ระดับ module
    และห้ามเรียก `setStyleSheet` นอก `theme.py`: ใช้ objectName หรือ property (`kind`, `state`) กับ
    selector ใน stylesheet ของ theme แทน (มีเทสต์บังคับ; เปลี่ยน property แล้วเรียก `widgets.repolish`)
    การเปลี่ยนธีมสร้างหน้าต่างใหม่ที่เปิดเคส session และแท็บเดิม (`MainWindow.restyle`) และรอถ้ามีงาน
    ทำอยู่หรือมีการแก้ไขที่ยังไม่บันทึก; ข้อความในธีมมืดต้องมี contrast อย่างน้อย 4.5:1 (มีเทสต์บังคับ)
    ส่วนรายงานและ PDF เป็นขาวดำเหมือนกระดาษเสมอ
36e. การเคลื่อนไหวของแอป desktop อยู่ใน `packages/desktop/ui/motion.py`: หน้าและแท็บค่อย ๆ ปรากฏ
    (150 ms, เอา effect ออกเมื่อจบ) และข้อความสั้นแบบ toast (`MainWindow.notify`, หน้า session ส่งผ่าน
    สัญญาณ `notify`) แทนข้อความชั่วคราวในแถบสถานะ; ข้อความที่ค้างระหว่างทำงานยังอยู่ในแถบสถานะ
    ต้องเคารพ "ลดการเคลื่อนไหว" ของเครื่อง (macOS/Windows) เว้นแต่ผู้ใช้เลือกเองใน ตั้งค่า → การเคลื่อนไหว
    (QSettings `appearance/motion`) และ toast เป็นข้อความธรรมดา (ไม่ตีความ HTML) ที่ screen reader อ่านได้
36f. หน้าจอ desktop ต้องไม่ค้างกับข้อมูลขนาดจริง: เติมตารางภายใน `widgets.filling(table)` (คอลัมน์
    ResizeToContents วัดใหม่ทุกช่องทำให้ transcript 500 บรรทัดใช้ 6 วินาที; มีเทสต์จับเวลาใน
    `tests/test_desktop_speed.py`), หน้ารายงานวาดตัวอย่าง A4 เฉพาะตอนเห็นบนจอ, พจนานุกรมไทยโหลด
    เบื้องหลังตอนเปิดโปรแกรม (`clan_words.warm_up`), และงานที่นานกว่าเสี้ยววินาทีรันผ่าน `TaskRunner`
    พร้อมหน้าต่างความคืบหน้า (สำรองข้อมูลยกเลิกได้และไม่ทิ้งไฟล์ `.partial`; กู้คืนแสดงความคืบหน้าตามไบต์)
36g. `DesktopService` (`packages/desktop/core/service.py`) ประกอบจาก mixin หนึ่งตัวต่อหนึ่งส่วนของ workflow
    ใน `packages/desktop/core/workflow/` (settings, clinic_speaker, maintenance, cases, recordings,
    transcripts, findings, reports) และ error กับ helper ที่ใช้ร่วมกันอยู่ใน `workflow/common.py`;
    เพิ่ม method ใหม่ในไฟล์ของส่วนนั้น และ import error จาก `packages.desktop.core` เหมือนเดิม
    ฝั่งหน้าจอทำแบบเดียวกัน: `MainWindow` (`packages/desktop/ui/main_window.py`) เก็บการสร้างหน้าต่าง
    layout การนำทาง และสถานะหน้าต่าง ส่วนงานอื่นอยู่ใน mixin ที่ `packages/desktop/ui/window/`
    (case_view, case_actions, settings_actions, updates, appearance, backup) และค่าที่ใช้ร่วมกันใน `window/common.py`
37. ขอบเขต term paper อยู่ใน `SCOPE_AND_DELIVERABLES.md` และการจับคู่หัวข้อกับหลักฐาน
    อยู่ใน `docs/TERM_PAPER_MAPPING.md`
38. ชื่อโครงการในโค้ด config และเอกสารที่ใช้งานอยู่คือ PasaScope เท่านั้น:
    path `apps/pasascope-app/`, ตัวแปร `PASASCOPE_*`, class `PasaScope*`.
    ชื่อเดิมอนุญาตเฉพาะในบันทึกย้อนหลัง ชื่อทรัพยากรภายนอก ตัวระบุที่บันทึกไปกับข้อมูล
    และโค้ดที่อ่านข้อมูลชื่อเดิม ตามรายการใน `docs/RENAME_FOLLOWUP.md`;
    `scripts/check_repo_consistency.py` บังคับกฎนี้

## ML status

Current ML runtime surface คือ **Reference evidence review** ใน `packages/ml/`,
`artifacts/reference_evidence/` และ provider ใน `apps/api`

Gate 1 artifact ล่าสุดมีสถานะ `promoted_candidate` ในเชิง engineering:

- sensitivity: `0.8862`
- sensitivity lower 95% CI: `0.8091`
- specificity: `0.6124`
- ECE: `0.0332`
- abstention: `0.3166`

Reference evidence เป็น opt-in และ fail-closed: ค่าเริ่มต้นของ
`PASASCOPE_REFERENCE_ARTIFACT_DIR` (`artifacts/reference_evidence/current`)
ไม่มีอยู่ใน repository และ `candidate-v1` ที่ commit ไว้มี `reference_cells.csv`
เฉพาะบรรทัดหัวตาราง provider จึงรายงาน `unavailable` จนกว่าจะชี้ไปยัง artifact
ที่ผ่านการอนุมัติตาม `docs/ML_REFERENCE_EVIDENCE_OPERATIONS.md`

คำว่า `promoted_candidate` ไม่ได้หมายถึง clinical validation หรืออนุญาตให้แสดง
diagnosis/probability. Runtime therapist workflow ยังคงแสดงเฉพาะ evidence/review
cues แบบ fail-closed และไม่ใส่ผลลงรายงานอัตโนมัติ

## Version policy

- รุ่นผลิตภัณฑ์รวมใช้สาย `v1.7.x`
- component/schema/provider version tags ต้องสอดคล้องกับ maintained runtime ปัจจุบัน
- `README.md`, `PROJECT_STATUS.md` และหัวบนสุดของ `CHANGELOG.md` ต้องตรงกัน
- เอกสาร phase/spec/plan เก่าเป็น historical record ไม่ใช่คำสั่ง runtime

## Standard commands

```bash
# Active API
cd apps/api
PYTHONPATH=.:../..:../../src uvicorn app.main:app --reload --port 8000

# Active therapist frontend
cd apps/pasascope-app
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev

# Focused local verification (not a complete CI candidate)
cd /path/to/pasascope
bash scripts/check_project.sh
```

Complete CI candidate gates additionally run dependency audits, the Python
3.11/3.12/3.13 matrix, frontend lint/typecheck, UI audit, full therapist and
demo Playwright suites, and the transcript benchmark baseline gate.

## Rules for every agent

1. อ่านไฟล์นี้และ `AGENTS.md` ก่อนแก้โค้ด
2. ตรวจ branch และ `git status` ก่อนเริ่ม
3. ห้ามสร้าง therapist frontend/backend ชุดใหม่โดยไม่เพิ่ม ADR
4. ห้ามเปลี่ยน canonical path โดยแก้เอกสารเพียงบางไฟล์
5. ห้าม commit generated/local files
6. ห้ามใช้ข้อมูลจริงหรือ identifier ใน fixtures/logs
7. หลังเปลี่ยนโครงสร้าง ต้องอัปเดตไฟล์นี้ README และ CHANGELOG พร้อมกัน
8. อย่าอ้างว่า clinical-ready จาก software tests หรือ Gate 1
