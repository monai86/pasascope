/**
 * Thai wording for the reasons `workflow-gates.ts` gives when an action is
 * blocked, keyed by the English reason. The gate functions stay the single
 * place that decides *whether* and *why*; this only supplies the other language.
 * A test fails if a reason in `workflow-gates.ts` has no entry here.
 */
export const GATE_REASONS_TH: Readonly<Record<string, string>> = {
  "Complete the session details (child/client, date, time, and clinician) before starting transcript review.":
    "กรอกรายละเอียดเซสชันให้ครบ (เด็ก/ผู้รับบริการ วันที่ เวลา และนักบำบัด) ก่อนเริ่มทบทวนบทถอดเสียง",
  "Complete the transcript setup fields and confirm both review requirements before starting transcript review.":
    "กรอกการตั้งค่าบทถอดเสียงให้ครบ และยืนยันข้อกำหนดในการทบทวนทั้งสองข้อ ก่อนเริ่มทบทวนบทถอดเสียง",
  "Add transcript text in Source Material before starting transcript review.":
    "เพิ่มข้อความบทถอดเสียงในขั้นแหล่งข้อมูลก่อนเริ่มทบทวนบทถอดเสียง",
  "Wait until a draft transcript is available before starting transcript review.":
    "รอให้มีร่างบทถอดเสียงก่อน จึงเริ่มทบทวนบทถอดเสียงได้",
  "Complete the session details (child/client, date, time, and clinician) before continuing to source material.":
    "กรอกรายละเอียดเซสชันให้ครบ (เด็ก/ผู้รับบริการ วันที่ เวลา และนักบำบัด) ก่อนไปต่อที่แหล่งข้อมูล",
  "Check the confirmation box to verify caregiver consent was obtained.":
    "ติ๊กช่องยืนยันว่าได้รับความยินยอมจากผู้ดูแลแล้ว",
  "Save a transcript and review it before extracting features.":
    "บันทึกบทถอดเสียงและทบทวนก่อนสกัดค่าทางภาษา",
  "Save the transcript to the session before extracting features.":
    "บันทึกบทถอดเสียงลงในเซสชันก่อนสกัดค่าทางภาษา",
  "A persisted session is required before extracting features.":
    "ต้องมีเซสชันที่บันทึกในระบบแล้วก่อนสกัดค่าทางภาษา",
  "Add transcript lines before exporting.": "เพิ่มบรรทัดในบทถอดเสียงก่อนส่งออก",
  "Complete transcript review and attestation before regenerating findings.":
    "ทบทวนและรับรองบทถอดเสียงให้เสร็จก่อนสร้างผลการวิเคราะห์ใหม่",
  "The backend is unavailable; evidence review cannot be generated until the connection is restored.":
    "ติดต่อเซิร์ฟเวอร์ไม่ได้ จึงยังสร้างการทบทวนหลักฐานไม่ได้จนกว่าจะเชื่อมต่อได้อีกครั้ง",
  "The evidence readiness check is blocked; resolve the blocking condition before generating evidence review.":
    "การตรวจความพร้อมของหลักฐานยังไม่ผ่าน แก้เงื่อนไขที่ติดอยู่ก่อนสร้างการทบทวนหลักฐาน",
  "AI-assisted review requires extracted features from a reviewed, attested transcript.":
    "การทบทวนโดยมี AI ช่วย ต้องมีค่าทางภาษาที่สกัดจากบทถอดเสียงที่ทบทวนและรับรองแล้ว",
  "AI-assisted review requires a saved, reviewed, and attested transcript.":
    "การทบทวนโดยมี AI ช่วย ต้องมีบทถอดเสียงที่บันทึก ทบทวน และรับรองแล้ว",
  "Regenerate findings from the current attested transcript before generating AI-assisted review.":
    "สร้างผลการวิเคราะห์ใหม่จากบทถอดเสียงที่รับรองฉบับปัจจุบัน ก่อนสร้างการทบทวนโดยมี AI ช่วย",
  "Regenerate findings from the current attested transcript before approving reviewed cues.":
    "สร้างผลการวิเคราะห์ใหม่จากบทถอดเสียงที่รับรองฉบับปัจจุบัน ก่อนอนุมัติข้อสังเกตที่ทบทวนแล้ว",
  "Approve reviewed cues requires extracted signals or an evidence review. Review and attest the transcript, then extract features.":
    "การอนุมัติข้อสังเกตที่ทบทวนแล้ว ต้องมีค่าที่สกัดได้หรือการทบทวนหลักฐาน ให้ทบทวนและรับรองบทถอดเสียง แล้วสกัดค่าทางภาษา",
  "Add transcript lines before attesting.": "เพิ่มบรรทัดในบทถอดเสียงก่อนรับรอง",
  "Run transcript QA before attesting.": "ตรวจคุณภาพบทถอดเสียงก่อนรับรอง",
  "Resolve the QA failures before attesting.": "แก้ปัญหาที่พบจากการตรวจคุณภาพก่อนรับรอง",
};

/** The one reason with a backend-supplied tail: translate the lead-in, keep the tail. */
export const GATE_REASON_PREFIXES_TH: ReadonlyArray<readonly [string, string]> = [
  ["Evidence readiness check is blocked: ", "การตรวจความพร้อมของหลักฐานยังไม่ผ่าน: "],
];
