import type { WorkflowStatus } from "@/components/status-badge";
import { defineMessages } from "@/i18n/messages";

/** Display names of the workflow statuses the backend reports. */
export const statusMessages = defineMessages<Record<WorkflowStatus, string>>({
  en: {
    Draft: "Draft",
    "Needs Review": "Needs Review",
    Attested: "Attested",
    Processing: "Processing",
    Failed: "Failed",
    Ready: "Ready",
    "Signed Off": "Signed Off",
    Withdrawn: "Withdrawn",
    "Awaiting Consent": "Awaiting Consent",
    "Ready for Audio": "Ready for Audio",
    Recording: "Recording",
    Uploading: "Uploading",
    Transcribing: "Transcribing",
    "CHA Generating": "CHA Generating",
    "ML Pending": "ML Pending",
    "Review Required": "Review Required",
    "Report Ready": "Report Ready",
  },
  th: {
    Draft: "ร่าง",
    "Needs Review": "รอทบทวน",
    Attested: "รับรองแล้ว",
    Processing: "กำลังประมวลผล",
    Failed: "ไม่สำเร็จ",
    Ready: "พร้อม",
    "Signed Off": "ลงนามแล้ว",
    Withdrawn: "ถอนแล้ว",
    "Awaiting Consent": "รอความยินยอม",
    "Ready for Audio": "พร้อมรับเสียง",
    Recording: "กำลังบันทึกเสียง",
    Uploading: "กำลังอัปโหลด",
    Transcribing: "กำลังถอดเสียง",
    "CHA Generating": "กำลังสร้างไฟล์ CHA",
    "ML Pending": "รอผลวิเคราะห์",
    "Review Required": "ต้องทบทวน",
    "Report Ready": "รายงานพร้อม",
  },
});
