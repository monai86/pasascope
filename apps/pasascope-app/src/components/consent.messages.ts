import { defineMessages } from "@/i18n/messages";

/** Caregiver consent form labels; kept apart from the audio catalog so Cases does not load recorder strings. */
type ConsentCopy = {
  verifying: string;
  externalTranscription: string;
};

export const consentMessages = defineMessages<ConsentCopy>({
  en: {
    verifying: "Verifying...",
    externalTranscription:
      "Recordings uploaded for transcription are sent to an external transcription service. Make sure the caregiver's consent covers this.",
  },
  th: {
    verifying: "กำลังยืนยัน...",
    externalTranscription:
      "เสียงที่อัปโหลดเพื่อถอดเสียงจะถูกส่งไปยังบริการถอดเสียงภายนอก โปรดตรวจว่าความยินยอมของผู้ปกครองครอบคลุมเรื่องนี้แล้ว",
  },
});
