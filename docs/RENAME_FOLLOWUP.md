# ชื่อเดิมที่ยังเหลืออยู่ และสิ่งที่ต้องทำเองถ้าจะเปลี่ยน

โครงการเปลี่ยนชื่อจาก LinguaLens เป็น PasaScope แล้วในโค้ด config และเอกสารที่ใช้งานอยู่
ชื่อเดิมยังปรากฏในสามกลุ่มด้านล่างโดยตั้งใจ ตัวตรวจ `scripts/project_name_guard.py`
อนุญาตเฉพาะรายการเหล่านี้ และจะแจ้งเมื่อชื่อเดิมโผล่ที่อื่น

## 1. ทรัพยากรภายนอกที่ยังไม่ได้เปลี่ยนชื่อ

ชื่อเหล่านี้ชี้ไปยังของที่อยู่นอก repo ถ้าแก้เฉพาะใน repo ระบบจะหาของจริงไม่เจอ
ต้องเปลี่ยนที่ผู้ให้บริการก่อน แล้วค่อยแก้ที่นี่

| ชื่อ | อยู่ที่ | ถ้าจะเปลี่ยน |
|---|---|---|
| Cloudflare worker `lingualens-web` | `apps/pasascope-app/wrangler.jsonc` | สร้าง/เปลี่ยนชื่อ worker ใน Cloudflare, ย้าย route และ secret, แล้วแก้ `name` กับ `service` |
| ฐานข้อมูล `lingualens_assessment_v2` และ role `lingualens_assessment_app` | `apps/api/app/core/config.py`, `docker-compose.yml`, `scripts/postgres/init-assessment-v2.sql`, สคริปต์ `scripts/check_assessment_v2_*.py` | สร้างฐานข้อมูลและ role ใหม่หรือ `ALTER … RENAME`, อัปเดต connection string ใน secret store, ลบ volume ของ Docker ในเครื่องถ้าใช้ compose |
| โปรเจกต์ staging/production (`lingualens-staging`, `lingualens-production`, `lingualens-api-staging`, URL ของ Render/Vercel/Supabase) | runbook ใน `docs/` | เปลี่ยนชื่อที่ผู้ให้บริการ แล้วแก้ URL ใน runbook และค่า CORS |
| GitHub repository `monai86/lingualens` | เอกสารที่อ้าง URL | เปลี่ยนชื่อ repo บน GitHub (ลิงก์เดิมจะ redirect) |

## 2. ตัวระบุที่ถูกบันทึกไปกับข้อมูล

| ตัวระบุ | เหตุผลที่คงไว้ |
|---|---|
| `lingualens-thai-mixed-tokenizer-v1`, `lingualens-chat-subset-v1`, `lingualens-cha-parser-v1`, `lingualens-cha-serializer-v1` | เป็นรหัสเวอร์ชันที่ผูกกับ checksum ของผลวิเคราะห์ที่สร้างไว้แล้ว เปลี่ยนแล้วผลเดิมจะตรวจสอบย้อนหลังไม่ได้ ให้ออกรหัส `-v2` ชื่อใหม่เมื่อมีการเปลี่ยนพฤติกรรมจริง |
| `demo_mode: "lingualens-app-local"` | ค่าในไฟล์ข้อมูล demo (`data/demo/demo_manifest.json`) |
| `data/ml/LinguaLens_ML_Features_and_Results_Summary.xlsx` | ชื่อไฟล์ผลวิจัยที่อ้างในรายงานเดิม |

## 3. ความเข้ากันได้ย้อนหลังที่ใส่ไว้

ลบได้เมื่อแน่ใจว่าไม่มีเครื่องหรือระบบใดใช้ชื่อเดิมแล้ว

| สิ่งที่ยังรับชื่อเดิม | อยู่ที่ |
|---|---|
| ตัวแปร `LINGUALENS_*` (ชื่อ `PASASCOPE_*` ชนะเมื่อมีทั้งคู่) | `getenv_compat` ใน `apps/api/app/core/config.py`, `docker-compose.yml`, `scripts/check_project.sh` |
| ไฟล์ `.local/lingualens-app-repository.json` | `Settings.resolved_json_repository_path`, `scripts/report_transcript_review_time.py`, `scripts/clean_mock_data.py` |
| key ในเบราว์เซอร์ที่ขึ้นต้นด้วย `lingualens.` | `apps/pasascope-app/src/lib/storage-key-migration.ts` |

## สิ่งที่ไม่ได้แก้

บันทึกย้อนหลังคงชื่อเดิมไว้ตามที่เขียนในตอนนั้น: `docs/archive/`, `docs/release_artifacts/`,
`docs/plans/`, `docs/superpowers/`, `docs/readiness/`, `docs/frontend/`, `docs/core-speech-testbed/`,
`docs/ux/`, `reports/`, รายการเก่าใน `CHANGELOG.md` และ path `/Users/porschecaa/lingualens/…`
ที่อ้างเป็นหลักฐานในเอกสาร
