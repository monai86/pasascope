/**
 * Thai wording for the fixed English labels the Findings helpers derive from
 * workflow state. The helpers keep returning English (other code compares
 * against some of these values); this table is applied only where a label is
 * shown. Text that comes from the backend is not in this table and is shown
 * as it arrives.
 */
export const FINDINGS_LABELS_TH: Readonly<Record<string, string>> = {
  // Transcript quality
  Pass: "ผ่าน",
  Warning: "มีข้อควรระวัง",
  Blocked: "ระงับ",
  Pending: "รอดำเนินการ",
  // Analysis and evidence disposition
  "Current findings": "ผลการวิเคราะห์ฉบับปัจจุบัน",
  "Stale · regeneration required": "ล้าสมัย · ต้องสร้างใหม่",
  Processing: "กำลังประมวลผล",
  Failed: "ไม่สำเร็จ",
  "Not generated": "ยังไม่ได้สร้าง",
  Completed: "เสร็จแล้ว",
  "Insufficient data": "ข้อมูลไม่เพียงพอ",
  Unavailable: "ไม่มีข้อมูล",
  // Evidence availability
  "Input action required": "ต้องแก้ไขข้อมูลนำเข้า",
  "Outside the supported evidence scope": "อยู่นอกขอบเขตหลักฐานที่รองรับ",
  "Insufficient reference data": "ข้อมูลอ้างอิงไม่เพียงพอ",
  "Evidence service unavailable": "บริการหลักฐานใช้งานไม่ได้",
  "Evidence available": "มีหลักฐาน",
  "Reference comparison unavailable": "ไม่มีข้อมูลเทียบกับค่าอ้างอิง",
  // Pattern and profile evidence
  "No additional pattern cue": "ไม่พบข้อสังเกตเชิงรูปแบบเพิ่มเติม",
  "Additional evidence review suggested": "แนะนำให้ทบทวนหลักฐานเพิ่มเติม",
  "Pattern evidence not available": "ไม่มีหลักฐานเชิงรูปแบบ",
  "Comparable patterns observed": "พบรูปแบบที่เทียบเคียงได้",
  "Limited comparison": "เทียบเคียงได้จำกัด",
  "Not available": "ไม่มีข้อมูล",
  "below the reference IQR": "ต่ำกว่าช่วง IQR ของค่าอ้างอิง",
  "above the reference IQR": "สูงกว่าช่วง IQR ของค่าอ้างอิง",
  "within the reference IQR": "อยู่ในช่วง IQR ของค่าอ้างอิง",
  "value unavailable": "ไม่มีค่า",
  // Review points the app itself adds
  "Therapist attestation is required before feature extraction and report drafting.":
    "นักบำบัดต้องรับรองบทถอดเสียงก่อนสกัดค่าทางภาษาและร่างรายงาน",
  "Complete feature extraction after transcript review to populate report-ready evidence.":
    "สกัดค่าทางภาษาหลังทบทวนบทถอดเสียง เพื่อให้มีหลักฐานพร้อมสำหรับรายงาน",
  "Confirm transcript wording, feature context, and therapist-edited draft text before generating the report.":
    "ตรวจถ้อยคำในบทถอดเสียง บริบทของค่าทางภาษา และร่างที่นักบำบัดแก้ไข ก่อนสร้างรายงาน",
};
