import { defineMessages } from "@/i18n/messages";

/** Two-step verification and deleting the account, in Settings › Privacy & Security. */
type AccountSecurityCopy = {
  twoStep: {
    title: string;
    hint: string;
    loading: string;
    off: string;
    on: string;
    turnOn: string;
    starting: string;
    scan: string;
    qrAlt: string;
    manual: string;
    codeLabel: string;
    confirm: string;
    confirming: string;
    cancel: string;
    keepApp: string;
    turnedOn: string;
    turnOff: string;
    offTitle: string;
    offBody: string;
    turnedOff: string;
    wrongCode: string;
    incomplete: string;
    failed: string;
  };
  deleteAccount: {
    title: string;
    hint: string;
    button: string;
    dialogTitle: string;
    dialogBody: string;
    typeEmail: (email: string) => string;
    confirm: string;
    deleting: string;
    cancel: string;
    mismatch: string;
    partlyDeleted: string;
    failed: string;
  };
};

export const accountSecurityMessages = defineMessages<AccountSecurityCopy>({
  en: {
    twoStep: {
      title: "Two-step verification",
      hint: "Ask for a code from an authenticator app each time you sign in, as well as your password or Google.",
      loading: "Checking…",
      off: "Off",
      on: "On: signing in asks for a code from your authenticator app.",
      turnOn: "Turn on",
      starting: "Preparing…",
      scan: "Scan this QR code with an authenticator app, such as Google Authenticator or Microsoft Authenticator.",
      qrAlt: "QR code that adds PasaScope to an authenticator app",
      manual: "Cannot scan it? Enter this key in the app instead:",
      codeLabel: "Code from the app",
      confirm: "Confirm and turn on",
      confirming: "Checking…",
      cancel: "Cancel",
      keepApp: "Keep the app. Without it this account cannot be opened until the person who runs this site turns two-step verification off.",
      turnedOn: "Two-step verification is on.",
      turnOff: "Turn off",
      offTitle: "Turn off two-step verification?",
      offBody: "Signing in will ask for your password or Google only. You can turn it on again at any time.",
      turnedOff: "Two-step verification is off.",
      wrongCode: "That code is not right or has expired. Enter the code the app shows now.",
      incomplete: "Enter all 6 digits.",
      failed: "Two-step verification could not be changed. Check your connection and try again.",
    },
    deleteAccount: {
      title: "Delete account",
      hint: "Deletes this account with every case, session, recording, transcript and report in it. This cannot be undone.",
      button: "Delete account…",
      dialogTitle: "Delete this account and everything in it?",
      dialogBody: "Your cases, sessions, recordings, transcripts and reports are deleted, then the account itself. Download any report you want to keep first.",
      typeEmail: (email) => `To confirm, type your email address: ${email}`,
      confirm: "Delete account",
      deleting: "Deleting…",
      cancel: "Cancel",
      mismatch: "Type the email address exactly as shown.",
      partlyDeleted: "Your records were deleted, but the account itself could not be removed yet. Try again in a moment.",
      failed: "Nothing was deleted. Check your connection and try again.",
    },
  },
  th: {
    twoStep: {
      title: "การยืนยันสองขั้นตอน",
      hint: "ขอรหัสจากแอปยืนยันตัวตนทุกครั้งที่ลงชื่อเข้าใช้ นอกเหนือจากรหัสผ่านหรือ Google",
      loading: "กำลังตรวจสอบ…",
      off: "ปิดอยู่",
      on: "เปิดอยู่: การลงชื่อเข้าใช้จะขอรหัสจากแอปยืนยันตัวตน",
      turnOn: "เปิดใช้",
      starting: "กำลังเตรียม…",
      scan: "สแกนคิวอาร์โค้ดนี้ด้วยแอปยืนยันตัวตน เช่น Google Authenticator หรือ Microsoft Authenticator",
      qrAlt: "คิวอาร์โค้ดสำหรับเพิ่ม PasaScope ในแอปยืนยันตัวตน",
      manual: "สแกนไม่ได้ ให้พิมพ์คีย์นี้ในแอปแทน:",
      codeLabel: "รหัสจากแอป",
      confirm: "ยืนยันและเปิดใช้",
      confirming: "กำลังตรวจสอบ…",
      cancel: "ยกเลิก",
      keepApp: "เก็บแอปไว้ให้ดี ถ้าไม่มีแอป จะเปิดบัญชีนี้ไม่ได้จนกว่าผู้ดูแลเว็บจะปิดการยืนยันสองขั้นตอนให้",
      turnedOn: "เปิดการยืนยันสองขั้นตอนแล้ว",
      turnOff: "ปิดใช้",
      offTitle: "ปิดการยืนยันสองขั้นตอนหรือไม่",
      offBody: "การลงชื่อเข้าใช้จะขอแค่รหัสผ่านหรือ Google คุณเปิดใช้ใหม่ได้ทุกเมื่อ",
      turnedOff: "ปิดการยืนยันสองขั้นตอนแล้ว",
      wrongCode: "รหัสไม่ถูกต้องหรือหมดอายุแล้ว ใส่รหัสที่แอปแสดงอยู่ตอนนี้",
      incomplete: "ใส่รหัสให้ครบ 6 หลัก",
      failed: "เปลี่ยนการยืนยันสองขั้นตอนไม่สำเร็จ ตรวจการเชื่อมต่อแล้วลองอีกครั้ง",
    },
    deleteAccount: {
      title: "ลบบัญชี",
      hint: "ลบบัญชีนี้พร้อมเคส เซสชัน ไฟล์เสียง บทถอดเสียง และรายงานทั้งหมดในบัญชี กู้คืนไม่ได้",
      button: "ลบบัญชี…",
      dialogTitle: "ลบบัญชีนี้และข้อมูลทั้งหมดหรือไม่",
      dialogBody: "เคส เซสชัน ไฟล์เสียง บทถอดเสียง และรายงานของคุณจะถูกลบ แล้วจึงลบตัวบัญชี ถ้ามีรายงานที่ต้องการเก็บ ให้ดาวน์โหลดไว้ก่อน",
      typeEmail: (email) => `พิมพ์อีเมลของคุณเพื่อยืนยัน: ${email}`,
      confirm: "ลบบัญชี",
      deleting: "กำลังลบ…",
      cancel: "ยกเลิก",
      mismatch: "พิมพ์อีเมลให้ตรงตามที่แสดง",
      partlyDeleted: "ลบข้อมูลของคุณแล้ว แต่ยังลบตัวบัญชีไม่ได้ ลองอีกครั้งในอีกสักครู่",
      failed: "ยังไม่ได้ลบอะไร ตรวจการเชื่อมต่อแล้วลองอีกครั้ง",
    },
  },
});
