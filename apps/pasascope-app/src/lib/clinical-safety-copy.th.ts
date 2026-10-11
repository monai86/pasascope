/**
 * Thai wording of the clinical and safety copy in clinical-safety-copy.ts,
 * keyed by the same constant names. The English module stays the registry the
 * backend's report checks were written against; this is its Thai counterpart
 * for the interface.
 *
 * The non-diagnostic boundary uses the required label from
 * docs/ux/therapist-workflow/content-and-safety-language.md verbatim, and no
 * entry may use a phrase that document prohibits. Changing a sentence here
 * changes what every Thai screen tells a therapist, so the wording is pinned
 * by clinical-safety-copy-th.test.ts.
 */
import type { CLINICAL_SAFETY_COPY } from "@/lib/clinical-safety-copy";

export type SafetyCopyKey = (typeof CLINICAL_SAFETY_COPY)[number][0];

/** "The system helps organise evidence. Diagnosis is the specialist's role." */
const SAFETY_BOUNDARY = "ระบบช่วยจัดระเบียบหลักฐาน การวินิจฉัยเป็นหน้าที่ของผู้เชี่ยวชาญ";

export const CLINICAL_SAFETY_COPY_TH = {
  DECISION_SUPPORT_ONLY: "ใช้ประกอบการตัดสินใจเท่านั้น",
  NOT_DIAGNOSTIC_STATEMENT: "ไม่ใช่การวินิจฉัย",
  NON_DIAGNOSTIC_CLAIM: SAFETY_BOUNDARY,
  NOT_DIAGNOSTIC_BADGE: "ไม่ใช่การวินิจฉัย",
  SAFETY_NOTICE_DEFAULT: `${SAFETY_BOUNDARY} นักบำบัดต้องทบทวนก่อนนำไปใช้ทางคลินิก`,
  THERAPIST_REVIEW_REQUIRED_CLAUSE: "นักบำบัดต้องทบทวน",
  THERAPIST_REVIEW_REQUIRED: "นักบำบัดต้องทบทวน",
  THERAPIST_REVIEW_REMAINS_REQUIRED_CLAUSE: "นักบำบัดยังต้องทบทวน",
  THERAPIST_REVIEW_REMAINS_REQUIRED: "นักบำบัดยังต้องทบทวน",
  THERAPIST_REVIEW_AND_CONSENT_REQUIRED: "ยังต้องผ่านการทบทวนของนักบำบัดและการให้ความยินยอม",
  THERAPIST_SIGNOFF_CLAUSE: "นักบำบัดยังต้องทบทวนและลงนาม",
  THERAPIST_REVIEW_SIGNOFF_REQUIRED: "นักบำบัดยังต้องทบทวนและลงนาม",
  REVIEW_REQUIRED_LABEL: "ต้องทบทวน",
  TRANSCRIPT_REVIEW_REQUIRED_LABEL: "ต้องทบทวนบทถอดเสียง",
  DRAFT_TRANSCRIPT_READY_LABEL: "ร่างบทถอดเสียงพร้อมแล้ว — ต้องทบทวน",
  EXPORT_ELIGIBILITY_NOTE: "รายงานส่งออกได้ต่อเมื่อนักบำบัดทบทวนและลงนามแล้ว ร่างที่ล้าสมัยต้องสร้างใหม่",
  QA_INTERPRETATION_NOTE: "การตรวจคุณภาพช่วยในการทบทวนบทถอดเสียง และต้องให้นักบำบัดเป็นผู้แปลผล",
  DECISION_SUPPORT_ONLY_LABEL: "ใช้ประกอบการตัดสินใจเท่านั้น",
  THERAPIST_INTERPRETATION_REQUIRED: "ต้องให้นักบำบัดเป็นผู้แปลผล",
  THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE: "ต้องให้นักบำบัดเป็นผู้แปลผล",
  INTERPRETATION_HINT: "ร่างเชิงพรรณนาที่นักบำบัดแก้ไขได้ ไม่ใช่การวินิจฉัยหรือข้อสรุปสุดท้าย",
  DRAFT_ASR_TRANSCRIPT_LABEL: "ร่างบทถอดเสียงจากระบบรู้จำเสียง — นักบำบัดต้องทบทวน",
  NON_DIAGNOSTIC_SCORE_CAUTION: "ค่าจากต้นแบบงานวิจัย ไม่ใช่ผลวินิจฉัย ต้องใช้ดุลยพินิจทางคลินิกของนักบำบัด",
  LONGITUDINAL_DELTA_CAUTION: "เป็นผลต่างเชิงตัวเลขเพื่อการพรรณนาเท่านั้น ยังแปลความหมายทางคลินิกไม่ได้ ไม่ใช่เครื่องมือวินิจฉัย",
  EXPERIMENTAL_ASR_CAUTION: "การถอดเสียงอัตโนมัติยังอยู่ในขั้นทดลองและยังไม่ผ่านการตรวจสอบทางคลินิก นักบำบัดต้องทบทวน",
  LIMITATION_TEXT:
    "รายงานนี้สร้างโดยต้นแบบระบบสนับสนุนการตัดสินใจทางคลินิก ไม่ใช่เครื่องมือวินิจฉัย บทถอดเสียง ค่าที่วัดได้ บทสรุปที่มี AI ช่วย และเนื้อหารายงานทั้งหมด ต้องได้รับการทบทวนและลงนามโดยนักบำบัดหรือผู้เชี่ยวชาญที่มีคุณสมบัติ",
} as const satisfies Record<SafetyCopyKey, string>;
