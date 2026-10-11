import { describe, expect, it } from "vitest";

import { CLINICAL_SAFETY_COPY } from "@/lib/clinical-safety-copy";
import { CLINICAL_SAFETY_COPY_TH } from "@/lib/clinical-safety-copy.th";
import { safetyCopy } from "@/lib/safety-copy";
import { findEmbeddedLabels } from "./support/single-sourcing";

// Phrases docs/ux/therapist-workflow/content-and-safety-language.md forbids in
// any interface, report or notification text.
const PROHIBITED_PHRASES = [
  "ตรวจพบออทิสติก",
  "ไม่เป็นออทิสติก",
  "ความน่าจะเป็น ASD",
  "ASD score",
  "diagnosed by system",
  "ASD probability",
];

const REQUIRED_SAFETY_BOUNDARY = "ระบบช่วยจัดระเบียบหลักฐาน การวินิจฉัยเป็นหน้าที่ของผู้เชี่ยวชาญ";

describe("Thai clinical safety copy", () => {
  it("translates exactly the strings the English registry holds", () => {
    expect(Object.keys(CLINICAL_SAFETY_COPY_TH).sort()).toEqual(CLINICAL_SAFETY_COPY.map(([name]) => name).sort());
  });

  it("states the non-diagnostic boundary with the required Thai label", () => {
    expect(CLINICAL_SAFETY_COPY_TH.NON_DIAGNOSTIC_CLAIM).toBe(REQUIRED_SAFETY_BOUNDARY);
    expect(CLINICAL_SAFETY_COPY_TH.SAFETY_NOTICE_DEFAULT.startsWith(REQUIRED_SAFETY_BOUNDARY)).toBe(true);
  });

  it("uses no prohibited diagnostic wording in either language", () => {
    for (const locale of ["en", "th"] as const) {
      for (const [name, text] of Object.entries(safetyCopy(locale))) {
        for (const phrase of PROHIBITED_PHRASES) {
          expect(text.includes(phrase), `${locale} ${name} contains "${phrase}"`).toBe(false);
        }
      }
    }
  });

  it("leaves no Thai entry empty or untranslated", () => {
    const english = Object.fromEntries(CLINICAL_SAFETY_COPY);
    for (const [name, text] of Object.entries(CLINICAL_SAFETY_COPY_TH)) {
      expect(text.trim().length, name).toBeGreaterThan(0);
      expect(text, name).not.toBe(english[name]);
      expect(/[฀-๿]/.test(text), `${name} has no Thai text`).toBe(true);
    }
  });

  it("pins the reviewed Thai wording", () => {
    expect(CLINICAL_SAFETY_COPY_TH).toMatchInlineSnapshot(`
      {
        "DECISION_SUPPORT_ONLY": "ใช้ประกอบการตัดสินใจเท่านั้น",
        "DECISION_SUPPORT_ONLY_LABEL": "ใช้ประกอบการตัดสินใจเท่านั้น",
        "DRAFT_ASR_TRANSCRIPT_LABEL": "ร่างบทถอดเสียงจากระบบรู้จำเสียง — นักบำบัดต้องทบทวน",
        "DRAFT_TRANSCRIPT_READY_LABEL": "ร่างบทถอดเสียงพร้อมแล้ว — ต้องทบทวน",
        "EXPERIMENTAL_ASR_CAUTION": "การถอดเสียงอัตโนมัติยังอยู่ในขั้นทดลองและยังไม่ผ่านการตรวจสอบทางคลินิก นักบำบัดต้องทบทวน",
        "EXPORT_ELIGIBILITY_NOTE": "รายงานส่งออกได้ต่อเมื่อนักบำบัดทบทวนและลงนามแล้ว ร่างที่ล้าสมัยต้องสร้างใหม่",
        "INTERPRETATION_HINT": "ร่างเชิงพรรณนาที่นักบำบัดแก้ไขได้ ไม่ใช่การวินิจฉัยหรือข้อสรุปสุดท้าย",
        "LIMITATION_TEXT": "รายงานนี้สร้างโดยต้นแบบระบบสนับสนุนการตัดสินใจทางคลินิก ไม่ใช่เครื่องมือวินิจฉัย บทถอดเสียง ค่าที่วัดได้ บทสรุปที่มี AI ช่วย และเนื้อหารายงานทั้งหมด ต้องได้รับการทบทวนและลงนามโดยนักบำบัดหรือผู้เชี่ยวชาญที่มีคุณสมบัติ",
        "LONGITUDINAL_DELTA_CAUTION": "เป็นผลต่างเชิงตัวเลขเพื่อการพรรณนาเท่านั้น ยังแปลความหมายทางคลินิกไม่ได้ ไม่ใช่เครื่องมือวินิจฉัย",
        "NON_DIAGNOSTIC_CLAIM": "ระบบช่วยจัดระเบียบหลักฐาน การวินิจฉัยเป็นหน้าที่ของผู้เชี่ยวชาญ",
        "NON_DIAGNOSTIC_SCORE_CAUTION": "ค่าจากต้นแบบงานวิจัย ไม่ใช่ผลวินิจฉัย ต้องใช้ดุลยพินิจทางคลินิกของนักบำบัด",
        "NOT_DIAGNOSTIC_BADGE": "ไม่ใช่การวินิจฉัย",
        "NOT_DIAGNOSTIC_STATEMENT": "ไม่ใช่การวินิจฉัย",
        "QA_INTERPRETATION_NOTE": "การตรวจคุณภาพช่วยในการทบทวนบทถอดเสียง และต้องให้นักบำบัดเป็นผู้แปลผล",
        "REVIEW_REQUIRED_LABEL": "ต้องทบทวน",
        "SAFETY_NOTICE_DEFAULT": "ระบบช่วยจัดระเบียบหลักฐาน การวินิจฉัยเป็นหน้าที่ของผู้เชี่ยวชาญ นักบำบัดต้องทบทวนก่อนนำไปใช้ทางคลินิก",
        "THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE": "ต้องให้นักบำบัดเป็นผู้แปลผล",
        "THERAPIST_INTERPRETATION_REQUIRED": "ต้องให้นักบำบัดเป็นผู้แปลผล",
        "THERAPIST_REVIEW_AND_CONSENT_REQUIRED": "ยังต้องผ่านการทบทวนของนักบำบัดและการให้ความยินยอม",
        "THERAPIST_REVIEW_REMAINS_REQUIRED": "นักบำบัดยังต้องทบทวน",
        "THERAPIST_REVIEW_REMAINS_REQUIRED_CLAUSE": "นักบำบัดยังต้องทบทวน",
        "THERAPIST_REVIEW_REQUIRED": "นักบำบัดต้องทบทวน",
        "THERAPIST_REVIEW_REQUIRED_CLAUSE": "นักบำบัดต้องทบทวน",
        "THERAPIST_REVIEW_SIGNOFF_REQUIRED": "นักบำบัดยังต้องทบทวนและลงนาม",
        "THERAPIST_SIGNOFF_CLAUSE": "นักบำบัดยังต้องทบทวนและลงนาม",
        "TRANSCRIPT_REVIEW_REQUIRED_LABEL": "ต้องทบทวนบทถอดเสียง",
      }
    `);
  });

  it("is single-sourced: no view restates a Thai safety sentence", () => {
    // Clauses that are also ordinary Thai words would match everyday copy, so
    // the scan covers the sentence-length entries.
    const sentences = Object.entries(CLINICAL_SAFETY_COPY_TH).filter(([, text]) => text.length >= 24);
    expect(findEmbeddedLabels(sentences, { exclude: ["src/lib/clinical-safety-copy.th.ts"] })).toEqual([]);
  });
});
