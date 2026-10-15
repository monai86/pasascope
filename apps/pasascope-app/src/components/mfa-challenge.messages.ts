import { defineMessages } from "@/i18n/messages";

/** The step after signing in, for an account with two-step verification. */
type MfaChallengeCopy = {
  title: string;
  body: string;
  codeLabel: string;
  verify: string;
  verifying: string;
  wrongCode: string;
  incomplete: string;
  failed: string;
  noFactor: string;
  lostApp: string;
  signOut: string;
};

export const mfaChallengeMessages = defineMessages<MfaChallengeCopy>({
  en: {
    title: "Enter your verification code",
    body: "This account uses two-step verification. Open your authenticator app and enter the 6-digit code it shows for PasaScope.",
    codeLabel: "6-digit code",
    verify: "Verify",
    verifying: "Checking…",
    wrongCode: "That code is not right or has expired. Enter the code the app shows now.",
    incomplete: "Enter all 6 digits.",
    failed: "The code could not be checked. Check your connection and try again.",
    noFactor: "This account's authenticator could not be found. Sign out and sign in again.",
    lostApp: "No longer have the authenticator app? Contact the person who runs this site to turn two-step verification off.",
    signOut: "Sign out",
  },
  th: {
    title: "ใส่รหัสยืนยัน",
    body: "บัญชีนี้เปิดการยืนยันสองขั้นตอนไว้ เปิดแอปยืนยันตัวตนแล้วใส่รหัส 6 หลักที่แอปแสดงสำหรับ PasaScope",
    codeLabel: "รหัส 6 หลัก",
    verify: "ยืนยัน",
    verifying: "กำลังตรวจสอบ…",
    wrongCode: "รหัสไม่ถูกต้องหรือหมดอายุแล้ว ใส่รหัสที่แอปแสดงอยู่ตอนนี้",
    incomplete: "ใส่รหัสให้ครบ 6 หลัก",
    failed: "ตรวจรหัสไม่ได้ ตรวจการเชื่อมต่อแล้วลองอีกครั้ง",
    noFactor: "ไม่พบแอปยืนยันตัวตนของบัญชีนี้ ให้ออกจากระบบแล้วลงชื่อเข้าใช้ใหม่",
    lostApp: "ไม่มีแอปยืนยันตัวตนแล้ว ให้ติดต่อผู้ดูแลเว็บนี้เพื่อปิดการยืนยันสองขั้นตอน",
    signOut: "ออกจากระบบ",
  },
});
