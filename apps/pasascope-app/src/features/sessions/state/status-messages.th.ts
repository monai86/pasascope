import { THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE } from "@/lib/clinical-safety-copy";
import { CLINICAL_SAFETY_COPY_TH } from "@/lib/clinical-safety-copy.th";

const interpretationRequired = CLINICAL_SAFETY_COPY_TH.THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE;

/**
 * Thai wording for the status and error messages the session controllers put
 * in workflow state, keyed by the English message. The controllers keep
 * writing English (the messages are also persisted and compared in tests);
 * this table is applied only where a message is shown. A message that is not
 * here, including one that comes from the backend, is shown as it arrives.
 */
export const STATUS_MESSAGES_TH: Readonly<Record<string, string>> = {
  // Loading and saving
  "Loading persisted workflow...": "กำลังโหลดงานที่บันทึกไว้...",
  "Loading persisted report...": "กำลังโหลดรายงานที่บันทึกไว้...",
  "Persisted transcript loaded.": "โหลดบทถอดเสียงที่บันทึกไว้แล้ว",
  "Persisted session loaded.": "โหลดเซสชันที่บันทึกไว้แล้ว",
  "Saving therapist transcript review...": "กำลังบันทึกการทบทวนบทถอดเสียงของนักบำบัด...",
  "Saving transcript source material...": "กำลังบันทึกแหล่งข้อมูลของบทถอดเสียง...",
  "Session intake saved locally. Transcript review can start when source material is ready.":
    "บันทึกการรับข้อมูลในเครื่องแล้ว เริ่มทบทวนบทถอดเสียงได้เมื่อแหล่งข้อมูลพร้อม",
  "Transcript ready for review.": "บทถอดเสียงพร้อมให้ทบทวน",
  "Transcript saved and ready for therapist review.": "บันทึกบทถอดเสียงแล้ว พร้อมให้นักบำบัดทบทวน",
  "Unsaved transcript edits.": "มีการแก้ไขบทถอดเสียงที่ยังไม่ได้บันทึก",
  "Failed to save transcript.": "บันทึกบทถอดเสียงไม่สำเร็จ",
  // QA and attestation
  "QA running...": "กำลังตรวจคุณภาพ...",
  "Save transcript edits before running QA.": "บันทึกการแก้ไขบทถอดเสียงก่อนตรวจคุณภาพ",
  "Transcript QA requires a backend-saved draft.": "การตรวจคุณภาพต้องใช้ร่างที่บันทึกในระบบแล้ว",
  "Backend QA was unavailable. Retry when the backend is available.": "ตรวจคุณภาพไม่ได้เพราะติดต่อเซิร์ฟเวอร์ไม่ได้ ลองใหม่เมื่อเชื่อมต่อได้",
  "Recording transcript attestation...": "กำลังบันทึกการรับรองบทถอดเสียง...",
  "No persistent transcript ID is available.": "ยังไม่มีรหัสของบทถอดเสียงที่บันทึกในระบบ",
  // Feature extraction and reviews
  "Feature extraction is locked until the transcript is reviewed and attested.":
    "การสกัดค่าทางภาษาจะล็อกอยู่จนกว่าจะทบทวนและรับรองบทถอดเสียง",
  "Review the transcript, run QA, and attest it before extracting features.":
    "ทบทวนบทถอดเสียง ตรวจคุณภาพ และรับรอง ก่อนสกัดค่าทางภาษา",
  "Extract transcript features before generating model-informed review cues.":
    "สกัดค่าทางภาษาจากบทถอดเสียงก่อนสร้างข้อสังเกตที่ใช้โมเดลช่วย",
  "Extract transcript features before generating AI-assisted review support.":
    "สกัดค่าทางภาษาจากบทถอดเสียงก่อนสร้างการทบทวนโดยมี AI ช่วย",
  "Evidence review requires extracted features from a reviewed transcript.":
    "การทบทวนหลักฐานต้องมีค่าทางภาษาที่สกัดจากบทถอดเสียงที่ทบทวนแล้ว",
  "AI-assisted review requires extracted features from a reviewed transcript.":
    "การทบทวนโดยมี AI ช่วย ต้องมีค่าทางภาษาที่สกัดจากบทถอดเสียงที่ทบทวนแล้ว",
  [`Evidence review generated. ${THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE}.`]: `สร้างการทบทวนหลักฐานแล้ว ${interpretationRequired}`,
  [`AI-assisted review generated. ${THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE}.`]: `สร้างการทบทวนโดยมี AI ช่วยแล้ว ${interpretationRequired}`,
  "ML review unavailable — backend verification required.": "ยังทบทวนด้วย ML ไม่ได้ ต้องให้เซิร์ฟเวอร์ตรวจยืนยันก่อน",
  "AI-assisted review unavailable — backend verification required.": "ยังทบทวนโดยมี AI ช่วยไม่ได้ ต้องให้เซิร์ฟเวอร์ตรวจยืนยันก่อน",
  "Cue review was not saved.": "ไม่ได้บันทึกการทบทวนข้อสังเกต",
  "Evidence review state was not saved.": "ไม่ได้บันทึกสถานะการทบทวนหลักฐาน",
  "Reviewed cues acknowledged and recorded server-side.": "รับทราบข้อสังเกตที่ทบทวนแล้ว และบันทึกในระบบแล้ว",
  "Reviewed cues acknowledgement was not recorded.": "ไม่ได้บันทึกการรับทราบข้อสังเกตที่ทบทวนแล้ว",
  // Report
  "Generating report draft...": "กำลังสร้างร่างรายงาน...",
  "Report generation failed.": "สร้างรายงานไม่สำเร็จ",
  "Report generation is locked until the transcript is reviewed and attested.":
    "การสร้างรายงานจะล็อกอยู่จนกว่าจะทบทวนและรับรองบทถอดเสียง",
  "Report generation is locked until language-sample features are extracted.":
    "การสร้างรายงานจะล็อกอยู่จนกว่าจะสกัดค่าทางภาษาจากตัวอย่างภาษา",
  "Review the transcript, run QA, and attest it before generating a report.":
    "ทบทวนบทถอดเสียง ตรวจคุณภาพ และรับรอง ก่อนสร้างรายงาน",
  "Extract language-sample features from the attested transcript before generating a report.":
    "สกัดค่าทางภาษาจากบทถอดเสียงที่รับรองแล้วก่อนสร้างรายงาน",
  "Report draft loaded.": "โหลดร่างรายงานแล้ว",
  "Finalized report loaded.": "โหลดรายงานที่ลงนามแล้ว",
  "Safety check failed.": "การตรวจความปลอดภัยไม่ผ่าน",
  "Saving report draft...": "กำลังบันทึกร่างรายงาน...",
  "Report draft saved.": "บันทึกร่างรายงานแล้ว",
  "Saved, but safety validation issues exist.": "บันทึกแล้ว แต่ยังมีปัญหาจากการตรวจความปลอดภัย",
  "Failed to save report.": "บันทึกรายงานไม่สำเร็จ",
  "Report finalized.": "ลงนามรายงานแล้ว",
  "Report finalization failed.": "ลงนามรายงานไม่สำเร็จ",
  "Creating a report revision...": "กำลังสร้างฉบับแก้ไขของรายงาน...",
  "Draft revision created. Review and save it before sign-off.": "สร้างร่างฉบับแก้ไขแล้ว ทบทวนและบันทึกก่อนลงนาม",
  "Report revision failed.": "สร้างฉบับแก้ไขของรายงานไม่สำเร็จ",
  "Markdown report exported.": "ส่งออกรายงานเป็น Markdown แล้ว",
  "HTML report exported.": "ส่งออกรายงานเป็น HTML แล้ว",
  "Export failed.": "ส่งออกไม่สำเร็จ",
  "Caregiver share status recorded locally. No external delivery was sent.":
    "บันทึกสถานะการแชร์กับผู้ดูแลไว้ในเครื่อง ไม่มีการส่งออกไปภายนอก",
  "Local demo share-link status recorded. No caregiver delivery endpoint was created.":
    "บันทึกสถานะลิงก์แชร์สำหรับสาธิตไว้ในเครื่อง ไม่ได้สร้างช่องทางส่งถึงผู้ดูแล",
  // Backend unavailable
  "Access denied.": "ไม่มีสิทธิ์เข้าถึง",
  "Backend unavailable.": "ติดต่อเซิร์ฟเวอร์ไม่ได้",
  "Backend unavailable. Edits remain unsaved and can be retried.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ การแก้ไขยังไม่ถูกบันทึก ลองใหม่ได้",
  "Backend unavailable. No AI-assisted review was generated or loaded.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ ไม่มีการสร้างหรือโหลดการทบทวนโดยมี AI ช่วย",
  "Backend unavailable. No ML review result was generated or loaded.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ ไม่มีการสร้างหรือโหลดผลการทบทวนด้วย ML",
  "Backend unavailable. No feature result was recorded.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ ไม่มีการบันทึกค่าทางภาษา",
  "Backend unavailable. No report draft was created.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ ไม่มีการสร้างร่างรายงาน",
  "Backend unavailable. Report edits remain unsaved.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ การแก้ไขรายงานยังไม่ถูกบันทึก",
  "Backend unavailable. The cue was not changed.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ ข้อสังเกตไม่ถูกเปลี่ยน",
  "Backend unavailable. The evidence disposition was not changed.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ สถานะของหลักฐานไม่ถูกเปลี่ยน",
  "Backend unavailable. The transcript was not exported.": "ติดต่อเซิร์ฟเวอร์ไม่ได้ ไม่ได้ส่งออกบทถอดเสียง",
  "Backend unavailable. Transcript input remains available for retry and was not persisted.":
    "ติดต่อเซิร์ฟเวอร์ไม่ได้ ข้อมูลบทถอดเสียงยังอยู่ให้ลองใหม่ แต่ยังไม่ถูกบันทึกในระบบ",
  "Backend report export was unavailable.": "ส่งออกรายงานจากเซิร์ฟเวอร์ไม่ได้",
  "Backend transcript export was unavailable.": "ส่งออกบทถอดเสียงจากเซิร์ฟเวอร์ไม่ได้",
};
