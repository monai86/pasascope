# จับคู่ Term Paper กับระบบและหลักฐาน

หัวข้อ: การประยุกต์ใช้ปัญญาประดิษฐ์เพื่อสนับสนุนการประเมินทางคลินิกสำหรับเด็กออทิสติก
(AI-Assisted Program for Clinical Assessment of Autism)

เอกสารนี้บอกว่าแต่ละส่วนของเล่มอ้างส่วนไหนของระบบ และใช้หลักฐานจากไฟล์ใด
ขอบเขตของงานอยู่ใน [`SCOPE_AND_DELIVERABLES.md`](../SCOPE_AND_DELIVERABLES.md)

## ข้อความหลักของงาน

ระบบใช้ AI ร่าง transcript จากเสียงและสกัดตัวชี้วัดทางภาษา เพื่อลดงานถอดเสียงของนักบำบัด
โดยนักบำบัดตรวจแก้และรับรองทุกขั้นก่อนนำผลไปใช้ ระบบไม่วินิจฉัยและไม่ให้คะแนนความเสี่ยง

## ตารางจับคู่

| ส่วนในเล่ม | ส่วนของระบบ | หลักฐาน |
|---|---|---|
| ที่มาและปัญหา | การถอดเสียงและวิเคราะห์ language sample ด้วยมือใช้เวลามาก | วรรณกรรมใน `docs/REFERENCES.md` |
| การออกแบบระบบ | Web app + API (`apps/lingualens-app`, `apps/api`) และ GUI offline (`packages/gui`) | `docs/PROJECT_SOURCE_OF_TRUTH.md`, `docs/DATA_FLOW_DIAGRAM.md` |
| AI ส่วนที่ 1: ถอดเสียง | Whisper บนเครื่อง + แยกผู้พูดเด็ก/ผู้ใหญ่ (`src/audio_pipeline`, provider `local_whisper`) | `reports/metrics/thai_asr_evaluation.md` |
| AI ส่วนที่ 2: ตัวชี้วัดภาษา | MLU-w, TTR, การผลัดกันพูด, echolalia cue, pronoun cue (`src/clinical_speech/thai_lsa.py`) | ส่วน feature drift ใน `thai_asr_evaluation.md`, เทสต์ `apps/api/tests/test_thai_feature_parity.py` |
| Human-in-the-loop | แก้ transcript, attest, ยืนยันหรือปัดตก cue, sign-off รายงาน | `reports/metrics/transcript_review_time.csv`, audit log |
| ผลการทดลองโมเดลจำแนก | การศึกษา classifier บนคลังข้อมูลภาษาอังกฤษสาธารณะ | `reports/ml/MODEL_RESULTS.md`, `reports/ml/ML_VALIDITY_DECISION.md`, `reports/ml/LEAKAGE_AND_CONFOUNDING_AUDIT.md` |
| ข้อจำกัด | ดูหัวข้อด้านล่าง | `KNOWN_LIMITATIONS.md` |
| งานในอนาคต | ข้อมูลเด็กไทยจริง, เกณฑ์อ้างอิงไทย, การ deploy จริง | `reports/ml/THAI_ACOUSTIC_NORMATIVE_DATA_PLAN.md`, `docs/PRODUCTION_SAAS_ROADMAP.md` |

## วิธีเล่าผลโมเดลจำแนก

ผลนี้เป็นเหตุผลของการออกแบบ ไม่ใช่จุดอ่อนที่ต้องซ่อน

- ภายในคลังข้อมูลเดียว (Eigsti) โมเดลแยก ASD กับ TD ได้ระดับปานกลาง: AUROC 0.62 (95% CI 0.54–0.71)
- แยก ASD กับ DD ได้ AUROC 0.77 และ TD กับ DD ได้ 0.83
- ข้ามคลังข้อมูล (Eigsti ↔ Nadig) ได้ AUROC 0.49 และ 0.56 ซึ่งใกล้การเดาสุ่ม
- ใช้แค่ metadata (สถานที่เก็บ งานที่ให้ทำ) ได้ AUROC 0.996 และใช้อายุอย่างเดียวได้ 0.986
  แปลว่าความแม่นยำสูงเมื่อรวมข้อมูลมาจาก confound ไม่ใช่ลักษณะภาษาของออทิสติก

ข้อสรุปที่เขียนได้: ตัวชี้วัดจาก transcript ยังไม่พอสำหรับคัดกรองอัตโนมัติข้ามบริบท
ระบบจึงแสดงตัวชี้วัดเชิงบรรยายและ cue ให้นักบำบัดตรวจ และไม่แสดงผลจำแนกใด ๆ

## ลำดับ demo

1. `LINGUALENS_ASR_LOCAL_WHISPER_ENABLED=true bash scripts/start_local.sh`
2. เปิดเคส บันทึก consent สร้าง session
3. อัดเสียงในเบราว์เซอร์แล้วกดอัปโหลด รอร่าง transcript (ป้ายแสดงว่า Whisper เป็นผู้ถอด)
4. ชี้จุดที่ ASR ผิด แก้ไข แล้ว attest
5. สกัด feature ดู cue แล้วยืนยันหรือปัดตก
6. ร่างรายงาน sign-off และ export
7. เปิด `./run_gui.sh --mock` เพื่อแสดงว่า pipeline เดียวกันทำงานได้โดยไม่มี server

ทดลองล่วงหน้าบนเครื่องที่จะใช้จริง ครั้งแรกที่ถอดเสียงจะช้ากว่าเพราะต้องโหลดโมเดล

## สิ่งที่ต้องเขียนเป็นข้อจำกัด

- ยังไม่มีข้อมูลเสียงเด็กไทยจริง ผล ASR มาจากเสียงจำลองของผู้ใหญ่จำนวนน้อย
- Whisper ไม่ได้ฝึกมาสำหรับเสียงเด็กเล็ก และการแยกผู้พูดอาศัยความต่างของเสียง
- echolalia cue และ pronoun cue เป็นกฎอย่างง่าย คำตอบปกติที่ใช้คำซ้ำกับผู้ใหญ่อาจถูกจับได้
- ไม่มีเกณฑ์อ้างอิงของเด็กไทย ระบบจึงไม่บอกว่าค่าใดปกติหรือผิดปกติ
- กราฟ radar ใน GUI ใช้ค่าเปรียบเทียบตามอายุที่ไม่มีแหล่งอ้างอิง ไม่ควรใช้ในเล่มหรือใน demo
- โมเดลจำแนกศึกษาบนข้อมูลภาษาอังกฤษเท่านั้น

## สิ่งที่ยังต้องทำเพื่อให้มีตัวเลขในเล่ม

1. อัดเสียงจำลอง 5–10 คลิปและถอด gold transcript ตาม `data/evaluation/README.md`
2. รัน `python scripts/evaluate_thai_asr.py` แล้วนำตารางจาก `reports/metrics/thai_asr_evaluation.md` ไปใช้
3. อัปโหลดคลิปเดียวกันผ่าน Web app แก้ร่างจน attest แล้วรัน `python scripts/report_transcript_review_time.py`
4. จับเวลาถอดเองทั้งคลิปของชุดเดียวกัน เพื่อเทียบกับเวลาแก้ร่าง
