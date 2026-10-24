# Project Source of Truth

เอกสารนี้เป็นจุดอ้างอิงหลักสำหรับคนและ AI agents ทุกตัวที่ทำงานใน repository
นี้ ไม่ว่าจะมาจาก Codex, Antigravity, Claude หรือเครื่องมืออื่น

## สถานะปัจจุบัน

- ชื่อโครงการ: **PasaScope (ภาษา-สโคป)** (เดิม LinguaLens)
- รุ่นโครงการ: `v1.8.0`
- branch หลัก: `main`
- ผลงานหลักและหัวข้อของ term paper: **โปรแกรมเดสก์ท็อป** `packages/desktop/`
  (PySide6, เปิดด้วย `./run_gui.sh` หรือคำสั่ง `pasascope`) รัน service layer ของ
  `apps/api` ในโปรแกรมเดียวบน SQLite ในเครื่อง ไม่มี server; ดู `SCOPE_AND_DELIVERABLES.md`
- ML/audio/research libraries: `src/`, `packages/` และ `scripts/`
- ระบบเป็น research/education prototype และ clinical review support เท่านั้น
- ระบบไม่วินิจฉัย ASD และยังไม่มี Thai clinical validation

## Canonical surfaces

| Surface | Canonical path | สถานะ |
|---|---|---|
| Desktop app (term paper deliverable) | `packages/desktop/` | Active |
| Shared service layer | `apps/api/app/services` (เรียกในโปรแกรมเดสก์ท็อปโดยตรง) | Active |
| Audio pipeline และกฎภาษาไทย | `src/audio_pipeline/`, `src/clinical_speech/`, `packages/features/`, `packages/cha/` | Active |
| Evaluation และงานวิจัย ML | `scripts/evaluate_*.py`, `reports/metrics/`, `packages/ml/`, `scripts/ml/`, `reports/ml/` | Active research tooling |
| หน้าดาวน์โหลด | `site/` (GitHub Pages) | Active |

## Removed paths

ถอดออกจาก working tree แล้ว กู้คืนได้จาก git tag `web-app-final`:

- Web app `apps/pasascope-app/` (Next.js), `shared/`, การ deploy (`Dockerfile`,
  `docker-compose*.yml`, `render.yaml`, `deploy/`), สคริปต์และเอกสาร Supabase,
  staging, SaaS, pilot launch (2026-10-23)
- โปรแกรม Tkinter เดิม `packages/gui/` และ TUI `packages/tui/` (2026-10-23)
- legacy research API `src/therapist_backend/`, `src/clinical_workflow/` และโมดูลที่ใช้
  เฉพาะกับมัน (`transcript_reviewer.py`, `therapist_report.py`, `reference_engine.py`,
  `speech_therapist_assistant.py`, `progress_tracking.py`, `eda.py`) (2026-10-23)
- `packages/analysis_contract/`, `packages/clinical_speech_artifacts/`, `packages/reports/`
  ซึ่งไม่มีส่วนใดของโปรแกรมเรียกใช้ (2026-10-23)
- ส่วนของ `apps/api` ที่ใช้เฉพาะ web server: FastAPI routes (`app/main.py`, `app/api/`),
  การ sign-in ด้วย Supabase (`app/auth/`, `app/core/security.py`), rate limit, worker/queue
  (`app/tasks/`), Alembic migrations ของ PostgreSQL, service ของบัญชี เป้าหมายการบำบัด
  privacy operation, AI review และ observability รวมถึงค่าตั้งของ web server ใน
  `app/core/config.py` (2026-10-25); ตารางในฐานข้อมูลยังคงเดิมเพื่อให้ไฟล์ SQLite
  ของผู้ใช้เปิดได้
- ก่อนหน้านั้น: `therapist-clinician-app/` (Vite/Capacitor), `public-screening/`,
  `presentation-dashboard/`, legacy benchmark pipeline
- `dist/`, `.local/`, `node_modules/`, `__pycache__/` เป็นไฟล์ที่สร้างขึ้นหรือข้อมูลในเครื่อง
  ห้าม commit

## Service-layer rules

1. Signed-off reports ต้องมี backend-generated signed snapshot, SHA-256 report
   hash, signer, version และ export timestamp เพื่อ audit/export ย้อนหลังได้;
   การแก้ report หลัง sign-off ต้องสร้าง draft revision ใหม่ที่อ้างถึง report
   เดิม ไม่แก้ signed snapshot เดิมแบบเงียบ
2. AI report drafting ต้อง default off และเปิดด้วย explicit environment หรือ
   organization opt-in เท่านั้น; ทุก AI draft request ต้องเก็บ provider/model/
   input-hash provenance และยังต้อง editable/rejectable ก่อน sign-off
3. เมื่อ transcript เปลี่ยน backend ต้องคง derived records เดิมไว้เพื่อ audit
   แต่ทำเครื่องหมาย findings และ report draft ที่มีอยู่เป็น `stale`; stale
   findings ห้ามใช้เป็น current input และ stale report ห้ามแก้, sign off หรือ
   export จนกว่าจะ regenerate จาก transcript version ปัจจุบัน ส่วน signed
   snapshot เดิมต้อง immutable
4. Log ต้องไม่บันทึก child identifier, transcript text, audio content, storage key,
   ชื่อไฟล์เสียงเดิม หรือ path ที่มี clinical identifiers
5. Audit events ต้องมี actor, action, target, outcome, timestamp และ correlation
    ID และต้องไม่บันทึก child identifiers, transcript text, audio content, storage
    keys, raw filenames, report excerpts หรือ clinical content

## Desktop and pipeline rules

6. ASR ใน v1 workflow: provider ที่ใช้ชื่อ engine ต้องรัน engine นั้นจริง ห้าม
    register provider ที่ติดป้ายข้อความจาก client เป็นผล ASR. `local_whisper`
    เป็น opt-in (`PASASCOPE_ASR_LOCAL_WHISPER_ENABLED`) รันบนเครื่อง API เท่านั้น
    และต้องปฏิเสธ strategy ที่ส่งเสียงออกนอกเครื่อง. เมื่อถอดเสียงไม่สำเร็จต้องรายงาน
    failed โดยไม่มีข้อความทดแทน ทั้งใน service layer และในโปรแกรมเดสก์ท็อป
7. ค่า feature ภาษาไทย (MLU-w, TTR, echolalia cue, pronoun cue) ต้องมาจากกฎชุด
    เดียวใน `src/clinical_speech/thai_lsa.py` ทั้งใน `apps/api` และโปรแกรมเดสก์ท็อป; ห้ามมีสูตร
    สำรองหรือค่าคงที่แทนค่าที่คำนวณไม่ได้ ให้ส่งเป็นค่าว่างแทน. สถานะของ guideline
    link ต้องเป็นคำบรรยายสิ่งที่นับได้ ไม่ใช่คำตัดสินเทียบเกณฑ์
8. โปรแกรมเดสก์ท็อปเรียก service ใน `apps/api/app/services` ตรง ๆ ผ่าน
    `packages/desktop/core/service.py` และต้องคงการตรวจความยินยอม audit event และ
    การตรวจความปลอดภัยของรายงานแบบเดียวกับ route ของ API; ห้ามมีสูตรวิเคราะห์ของตัวเอง.
    session ใหม่และการบันทึกเสียงต้องมีความยินยอมสถานะ `granted`. รายงานบนเดสก์ท็อปใช้
    provider `template_th` และ export PDF ด้วย Qt (ฟอนต์ไทยของระบบ)
9. โมเดลแยกเสียงเด็ก/ผู้ใหญ่ประจำคลินิก (`src/audio_pipeline/clinic_speaker_model.py`)
    เรียนบนเครื่องจาก transcript ที่รับรองแล้ว ร่างโดย Whisper และมีไฟล์เสียงในเครื่อง
    ของเด็กที่ความยินยอมยังเป็น `granted` เท่านั้น; ต้องมีอย่างน้อย 4 session จากเด็ก 2 คน
    และใช้แทนโมเดล USC ก็ต่อเมื่อ balanced accuracy แบบกันเด็กทีละคนสูงกว่าอย่างน้อย 2 จุด.
    ห้ามแจกโมเดลที่เทรนแล้วข้ามคลินิก. การเทรน เปิด/ปิด และล้าง ต้องมี audit event
    และป้าย ? ตามช่วงอายุยังมีผลเสมอ
10. ร่างภาษาอังกฤษตัดประโยคด้วยโมเดล logistic regression ที่อธิบายได้
    (`src/audio_pipeline/utterance_boundaries.py`, ไฟล์ `src/audio_pipeline/models/utterance_boundaries_en.json`
    ต้องรวมไปกับแอปตอน build) ทุกประโยคที่โมเดลเริ่มใหม่ต้องเก็บเหตุผลให้นักบำบัดอ่าน;
    ภาษาไทยยังใช้กฎช่วงหยุด 0.6 วินาที และ `PASASCOPE_UTTERANCE_BOUNDARIES=rule` ปิดโมเดลได้
10a. รายงาน session ของแอป desktop เขียนได้ทั้งไทย (`template_th`) และอังกฤษ (`template_clinic_en`)
    ด้วยถ้อยคำคงที่ หัวข้อเดียวกัน; PDF และตัวอย่างก่อนพิมพ์วาดด้วย `paint_report` ตัวเดียว
    ตามรูปแบบใน `docs/REPORT_LAYOUT.md`; ฟอนต์ TH Sarabun New (GPL + font exception) และ Sarabun (OFL) ใน `packages/desktop/ui/assets/fonts/`
    และโลโก้ `logo.png` ต้องรวมไปกับแอปตอน build พร้อมไฟล์ไลเซนส์ของฟอนต์
10b. Feature schema `features-basic-v3` เพิ่มตัวชี้วัดการผลัดกันพูด (`packages/features/turn_taking.py`);
    หน้าตัวชี้วัดและรายงานแสดงเฉพาะตัวหลักใน `labels.CORE_FEATURES` ตามหลักฐานใน `docs/FEATURE_GUIDE.md`
    และทุกตัวชี้วัดต้องมีคำอธิบายใน `packages/desktop/ui/feature_guide.py` (มีเทสต์บังคับ)
10c. แอป desktop แจกเป็น `.dmg` จาก `scripts/build_macos_dmg.py` และอัปเดตจาก GitHub Releases
    ตาม `docs/DESKTOP_RELEASE.md`; โมเดลเสียงดาวน์โหลดตอนใช้ครั้งแรกและตรวจ SHA-256 ทุกไฟล์
    (`packages/desktop/core/models.py`); การสร้าง release ต้องได้รับอนุญาตจากเจ้าของโครงการ
10d. แอป desktop มีธีมสว่างและมืด (`packages/desktop/ui/theme.py`, ชุดสี `LIGHT`/`DARK` ชื่อเดียวกัน)
    ค่าเริ่มต้นตามเครื่อง เลือกเองได้ที่ ตั้งค่า → ธีม (เก็บใน QSettings `appearance/theme`);
    widget ต้องอ่านสีจาก `theme.<NAME>` ตอนสร้างหรือวาด ห้ามคัดลอกสีไปเป็นค่าคงที่ระดับ module
    และห้ามเรียก `setStyleSheet` นอก `theme.py`: ใช้ objectName หรือ property (`kind`, `state`) กับ
    selector ใน stylesheet ของ theme แทน (มีเทสต์บังคับ; เปลี่ยน property แล้วเรียก `widgets.repolish`)
    การเปลี่ยนธีมสร้างหน้าต่างใหม่ที่เปิดเคส session และแท็บเดิม (`MainWindow.restyle`) และรอถ้ามีงาน
    ทำอยู่หรือมีการแก้ไขที่ยังไม่บันทึก; ข้อความในธีมมืดต้องมี contrast อย่างน้อย 4.5:1 (มีเทสต์บังคับ)
    ส่วนรายงานและ PDF เป็นขาวดำเหมือนกระดาษเสมอ
10e. การเคลื่อนไหวของแอป desktop อยู่ใน `packages/desktop/ui/motion.py`: หน้าและแท็บค่อย ๆ ปรากฏ
    (150 ms, เอา effect ออกเมื่อจบ) และข้อความสั้นแบบ toast (`MainWindow.notify`, หน้า session ส่งผ่าน
    สัญญาณ `notify`) แทนข้อความชั่วคราวในแถบสถานะ; ข้อความที่ค้างระหว่างทำงานยังอยู่ในแถบสถานะ
    ต้องเคารพ "ลดการเคลื่อนไหว" ของเครื่อง (macOS/Windows) เว้นแต่ผู้ใช้เลือกเองใน ตั้งค่า → การเคลื่อนไหว
    (QSettings `appearance/motion`) และ toast เป็นข้อความธรรมดา (ไม่ตีความ HTML) ที่ screen reader อ่านได้
10f. หน้าจอ desktop ต้องไม่ค้างกับข้อมูลขนาดจริง: เติมตารางภายใน `widgets.filling(table)` (คอลัมน์
    ResizeToContents วัดใหม่ทุกช่องทำให้ transcript 500 บรรทัดใช้ 6 วินาที; มีเทสต์จับเวลาใน
    `tests/test_desktop_speed.py`), หน้ารายงานวาดตัวอย่าง A4 เฉพาะตอนเห็นบนจอ, พจนานุกรมไทยโหลด
    เบื้องหลังตอนเปิดโปรแกรม (`clan_words.warm_up`), และงานที่นานกว่าเสี้ยววินาทีรันผ่าน `TaskRunner`
    พร้อมหน้าต่างความคืบหน้า (สำรองข้อมูลยกเลิกได้และไม่ทิ้งไฟล์ `.partial`; กู้คืนแสดงความคืบหน้าตามไบต์)
10h. เปิดโปรแกรม desktop: หน้าต่างโลโก้ (`ui/splash.py`) ขึ้นทุกครั้งระหว่างที่ thread เบื้องหลังโหลด
    ฐานข้อมูล ระบบถอดเสียง และพจนานุกรมไทย (`app._preload`; `packages.desktop.core` โหลด
    `DesktopService` เมื่อใช้ครั้งแรก) แล้วจางหายเมื่อหน้าต่างหลักพร้อม; ลดการเคลื่อนไหวแล้วไม่มีภาพเคลื่อนไหว
    หน้าแนะนำ 3 ขั้น (`ui/onboarding.py`: ยินดีต้อนรับและเลือกภาษา, ข้อควรรู้ที่ต้องติ๊กยอมรับ,
    ชื่อนักบำบัดที่ต้องกรอกและชื่อหน่วยงาน) ขึ้นเฉพาะเมื่อโฟลเดอร์ข้อมูลยังไม่มีชื่อนักบำบัด
    ข้อมูลอยู่นอกตัวโปรแกรม การอัปเดตหรือติดตั้งใหม่จึงไม่ทำให้หน้านี้กลับมา
10i. หน้าต่างหลักของ desktop จัดแบบ workbench ของโปรแกรมแก้โค้ด (`ui/workbench.py`): activity bar 48 px
    (หน้าแรก, เคส, ความรู้, ค้นหาคำสั่ง, ตั้งค่า), side bar ที่แสดงเคสเป็นต้นไม้พร้อม session หรือหัวข้อความรู้,
    พื้นที่แท็บที่เปิดหน้าแรก เคส session และความรู้ได้หลายแท็บพร้อมกัน (`ui/editors.py`: แต่ละ session มีหน้า
    ของตัวเอง แท็บที่ยังไม่บันทึกมี ●, ปิดแท็บถามเรื่องการแก้ไขที่ยังไม่บันทึก และปิดไม่ได้ระหว่างบันทึกหรือถอดเสียง),
    breadcrumbs, command palette (Ctrl/Cmd+Shift+P ทุกคำสั่ง, Ctrl/Cmd+P เปิดเคสหรือ session) และ status bar 22 px
    สลับแท็บไม่ถามอะไร และไม่สร้างต้นไม้เคสใหม่ (เลือกรายการที่ตรงกันเท่านั้น); ชุดสีเป็นแบบธีม 2026 ของโปรแกรมแก้โค้ด
    ไอคอนวาดเองในโค้ด ไม่ใช้ไอคอนหรือแบรนด์ของโปรแกรมอื่น
10g. `DesktopService` (`packages/desktop/core/service.py`) ประกอบจาก mixin หนึ่งตัวต่อหนึ่งส่วนของ workflow
    ใน `packages/desktop/core/workflow/` (settings, clinic_speaker, maintenance, cases, recordings,
    transcripts, findings, reports) และ error กับ helper ที่ใช้ร่วมกันอยู่ใน `workflow/common.py`;
    เพิ่ม method ใหม่ในไฟล์ของส่วนนั้น และ import error จาก `packages.desktop.core` เหมือนเดิม
    ฝั่งหน้าจอทำแบบเดียวกัน: `MainWindow` (`packages/desktop/ui/main_window.py`) เก็บการสร้างหน้าต่าง
    layout การนำทาง และสถานะหน้าต่าง ส่วนงานอื่นอยู่ใน mixin ที่ `packages/desktop/ui/window/`
    (case_view, case_actions, settings_actions, updates, appearance, backup) และค่าที่ใช้ร่วมกันใน `window/common.py`
11. ขอบเขต term paper อยู่ใน `SCOPE_AND_DELIVERABLES.md` และการจับคู่หัวข้อกับหลักฐาน
    อยู่ใน `docs/TERM_PAPER_MAPPING.md`
12. ชื่อโครงการในโค้ด config และเอกสารที่ใช้งานอยู่คือ PasaScope เท่านั้น:
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

- รุ่นผลิตภัณฑ์ใช้สาย `v1.8.x`
- `README.md`, `PROJECT_STATUS.md`, `pyproject.toml`, `packages/desktop` และหัวบนสุดของ
  `CHANGELOG.md` ต้องตรงกัน (`scripts/check_repo_consistency.py` ตรวจ)

## Standard commands

```bash
./run_gui.sh                      # เปิดโปรแกรมเดสก์ท็อป (--demo = ข้อมูลตัวอย่าง)
bash scripts/check_project.sh     # consistency, secret scan, เทสต์ Python ทั้งหมด
python scripts/build_macos_dmg.py # สร้าง .dmg
```

## Rules for every agent

1. อ่านไฟล์นี้และ `AGENTS.md` ก่อนแก้โค้ด
2. ตรวจ branch และ `git status` ก่อนเริ่ม
3. งานใหม่อยู่ในโปรแกรมเดสก์ท็อปและ service layer; ห้ามสร้าง web frontend หรือ backend ชุดใหม่โดยไม่เพิ่ม ADR
4. ห้ามเปลี่ยน canonical path โดยแก้เอกสารเพียงบางไฟล์
5. ห้าม commit generated/local files
6. ห้ามใช้ข้อมูลจริงหรือ identifier ใน fixtures/logs
7. หลังเปลี่ยนโครงสร้าง ต้องอัปเดตไฟล์นี้ README และ CHANGELOG พร้อมกัน
8. อย่าอ้างว่า clinical-ready จาก software tests หรือ Gate 1
