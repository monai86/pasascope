import { defineMessages } from "@/i18n/messages";

/** Caregiver consent form labels; kept apart from the audio catalog so Cases does not load recorder strings. */
type ConsentCopy = {
  signer: string;
  signerPlaceholder: string;
  date: string;
  notes: string;
  notesPlaceholder: string;
  verifying: string;
};

export const consentMessages = defineMessages<ConsentCopy>({
  en: {
    signer: "Signer relationship",
    signerPlaceholder: "e.g. Parent, Guardian",
    date: "Consent date",
    notes: "Verification notes",
    notesPlaceholder: "Add any verification comments, reference document numbers, or meeting details here.",
    verifying: "Verifying...",
  },
  th: {
    signer: "ความสัมพันธ์ของผู้ลงนาม",
    signerPlaceholder: "เช่น พ่อแม่ ผู้ปกครอง",
    date: "วันที่ให้ความยินยอม",
    notes: "บันทึกการยืนยัน",
    notesPlaceholder: "ใส่หมายเหตุการยืนยัน เลขที่เอกสารอ้างอิง หรือรายละเอียดการนัดพบได้ที่นี่",
    verifying: "กำลังยืนยัน...",
  },
});
