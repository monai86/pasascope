import { defineMessages } from "@/i18n/messages";

/** The public privacy page: what the app stores, where it goes and how to remove it. */
type PrivacyCopy = {
  title: string;
  intro: string;
  sections: ReadonlyArray<{ title: string; items: readonly string[] }>;
  contactTitle: string;
  contactWithEmail: (email: string) => string;
  contactWithoutEmail: string;
  backToSignIn: string;
};

export const privacyMessages = defineMessages<PrivacyCopy>({
  en: {
    title: "Privacy",
    intro:
      "PasaScope is a research and education prototype for reviewing child language samples. This page says what the app keeps, where it is processed and how to remove it.",
    sections: [
      {
        title: "What the app keeps",
        items: [
          "Your sign-in email address, and your name if you sign in with Google.",
          "The cases you create: the child code, age and notes you type in.",
          "Recordings you upload, the transcripts made from them, the language measures and the reports.",
        ],
      },
      {
        title: "Who can see it",
        items: [
          "Each account has its own workspace. Other users cannot open your cases, recordings, transcripts or reports.",
          "The people who operate this site can reach the database and the stored recordings to maintain the service.",
          "You can turn on two-step verification in Settings › Privacy & Security, so that signing in also needs a code from an authenticator app.",
        ],
      },
      {
        title: "Where it is processed",
        items: [
          "Accounts, records and recordings are stored with Supabase. The website runs on Vercel and the application server on Render.",
          "When you upload a recording for automatic transcription, the recording is sent to an external transcription service (currently Groq) and the text comes back as a draft.",
        ],
      },
      {
        title: "What you should not enter",
        items: [
          "Do not type a child's real name, ID number, address or other identifying details. Use a code instead.",
          "Record a child only after the caregiver has agreed to the recording, including that it is sent to an external service for transcription.",
        ],
      },
      {
        title: "Removing data",
        items: [
          "Withdrawing consent on a case removes its recordings from storage and stops that case's records from being used.",
          "You can delete your account and everything in it yourself, in Settings › Privacy & Security. Recordings are removed from storage first, then the records, then the account. A record that the account was deleted, with nothing from it, is kept.",
        ],
      },
    ],
    contactTitle: "Contact",
    contactWithEmail: (email) => `Questions: ${email}`,
    contactWithoutEmail: "For questions, contact the person who gave you access to this site.",
    backToSignIn: "Back to sign in",
  },
  th: {
    title: "ความเป็นส่วนตัว",
    intro:
      "PasaScope เป็นต้นแบบเพื่อการวิจัยและการศึกษา สำหรับทบทวนตัวอย่างภาษาของเด็ก หน้านี้บอกว่าแอปเก็บอะไร ประมวลผลที่ไหน และลบออกได้อย่างไร",
    sections: [
      {
        title: "สิ่งที่แอปเก็บ",
        items: [
          "อีเมลที่ใช้เข้าสู่ระบบ และชื่อของคุณถ้าเข้าสู่ระบบด้วย Google",
          "เคสที่คุณสร้าง ได้แก่ รหัสเด็ก อายุ และบันทึกที่คุณพิมพ์",
          "ไฟล์เสียงที่คุณอัปโหลด บทถอดเสียงที่ได้จากไฟล์นั้น ค่าทางภาษา และรายงาน",
        ],
      },
      {
        title: "ใครเห็นได้บ้าง",
        items: [
          "แต่ละบัญชีมีพื้นที่ทำงานของตัวเอง ผู้ใช้คนอื่นเปิดเคส ไฟล์เสียง บทถอดเสียง หรือรายงานของคุณไม่ได้",
          "ผู้ดูแลเว็บนี้เข้าถึงฐานข้อมูลและไฟล์เสียงที่เก็บไว้ได้ เพื่อดูแลระบบ",
          "คุณเปิดการยืนยันสองขั้นตอนได้ที่ ตั้งค่า › ความปลอดภัยและข้อมูล เพื่อให้การลงชื่อเข้าใช้ต้องใช้รหัสจากแอปยืนยันตัวตนด้วย",
        ],
      },
      {
        title: "ประมวลผลที่ไหน",
        items: [
          "บัญชี ข้อมูล และไฟล์เสียงเก็บไว้ที่ Supabase หน้าเว็บทำงานบน Vercel และเซิร์ฟเวอร์ของแอปทำงานบน Render",
          "เมื่อคุณอัปโหลดไฟล์เสียงเพื่อถอดเสียงอัตโนมัติ ไฟล์เสียงจะถูกส่งไปยังบริการถอดเสียงภายนอก (ปัจจุบันคือ Groq) แล้วได้ข้อความกลับมาเป็นร่าง",
        ],
      },
      {
        title: "สิ่งที่ไม่ควรกรอก",
        items: [
          "อย่าพิมพ์ชื่อจริง เลขประจำตัว ที่อยู่ หรือข้อมูลที่ระบุตัวเด็กได้ ให้ใช้รหัสแทน",
          "อัดเสียงเด็กเมื่อผู้ปกครองยินยอมแล้วเท่านั้น รวมถึงยินยอมให้ส่งเสียงไปถอดที่บริการภายนอก",
        ],
      },
      {
        title: "การลบข้อมูล",
        items: [
          "การถอนความยินยอมของเคส จะลบไฟล์เสียงของเคสนั้นออกจากที่เก็บ และหยุดการใช้ข้อมูลของเคสนั้น",
          "คุณลบบัญชีและข้อมูลทั้งหมดในบัญชีได้เองที่ ตั้งค่า › ความปลอดภัยและข้อมูล ระบบจะลบไฟล์เสียงออกจากที่เก็บก่อน แล้วจึงลบข้อมูล และลบบัญชี โดยเก็บไว้เพียงบันทึกว่ามีการลบบัญชี ซึ่งไม่มีข้อมูลใดจากบัญชีนั้น",
        ],
      },
    ],
    contactTitle: "ติดต่อ",
    contactWithEmail: (email) => `สอบถาม: ${email}`,
    contactWithoutEmail: "หากมีคำถาม ให้ติดต่อผู้ที่ให้สิทธิ์คุณเข้าใช้เว็บนี้",
    backToSignIn: "กลับไปหน้าเข้าสู่ระบบ",
  },
});
