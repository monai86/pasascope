/**
 * Thai wording for the fixed English labels the report helpers derive from
 * workflow state (save state, workflow status, safety status). The helpers
 * keep returning English; this table is applied only where a label is shown.
 */
export const REPORT_LABELS_TH: Readonly<Record<string, string>> = {
  // Save state
  "Locked snapshot": "ฉบับที่ล็อกแล้ว",
  "Blocked — regenerate": "ระงับ — ต้องสร้างใหม่",
  "Unsaved changes": "มีการแก้ไขที่ยังไม่ได้บันทึก",
  Saving: "กำลังบันทึก",
  Saved: "บันทึกแล้ว",
  "Save failed": "บันทึกไม่สำเร็จ",
  "Not saved": "ยังไม่ได้บันทึก",
  // Workflow status
  "Safety validation failed": "การตรวจความปลอดภัยไม่ผ่าน",
  "Never generated": "ยังไม่เคยสร้าง",
  Draft: "ร่าง",
  Reviewed: "ทบทวนแล้ว",
  Finalized: "ลงนามแล้ว",
  Stale: "ล้าสมัย",
  // Finalized safety status
  Passed: "ผ่าน",
  Pass: "ผ่าน",
  Warning: "มีข้อควรระวัง",
};
