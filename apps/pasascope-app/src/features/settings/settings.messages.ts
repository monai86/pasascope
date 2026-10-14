import type { SettingsSection } from "@/features/settings/services/settings-access";
import { defineMessages } from "@/i18n/messages";

type Line = readonly [label: string, value: string];

type SettingsCopy = {
  page: { title: string; description: string };
  sections: Record<SettingsSection, string>;
  nav: { label: string; allCategories: string; choose: string; workspace: string };
  descriptions: Record<SettingsSection, string>;
  account: {
    name: string;
    nameHint: string;
    nameEmpty: string;
    save: string;
    saving: string;
    saved: string;
    failed: string;
    email: string;
    workspace: string;
    workspaceValue: string;
    fallbackName: string;
    localOnly: string;
    localName: string;
  };
  display: {
    language: string;
    textSize: string;
    standard: string;
    large: string;
    motion: string;
    followDevice: string;
    reduce: string;
    motionHint: string;
  };
  workflow: {
    caseLanguage: string;
    caseLanguageHint: string;
    thai: string;
    english: string;
    facts: string;
    transcription: string;
    transcriptionExternal: string;
    transcriptionLocal: string;
    review: string;
    reviewValue: string;
    sharing: string;
    sharingValue: string;
  };
  privacy: {
    passwordTitle: string;
    passwordBody: string;
    newPassword: string;
    confirmPassword: string;
    passwordHint: (min: number) => string;
    tooShort: (min: number) => string;
    mismatch: string;
    samePassword: string;
    change: string;
    changing: string;
    changed: string;
    failed: string;
    everywhereTitle: string;
    everywhereBody: string;
    everywhereButton: string;
    everywhereBusy: string;
    everywhereFailed: string;
    localOnly: string;
    dataTitle: string;
    dataLines: readonly Line[];
    privacyPage: string;
  };
  help: {
    lines: readonly Line[];
    privacyPage: string;
  };
};

export const settingsMessages = defineMessages<SettingsCopy>({
  en: {
    page: {
      title: "Settings",
      description: "Your account, how the app looks on this device, and how new work starts.",
    },
    sections: {
      account: "Account",
      display: "Display",
      workflow: "Workflow",
      privacy: "Privacy & Security",
      help: "Help",
    },
    nav: {
      label: "Settings categories mobile",
      allCategories: "All settings categories",
      choose: "Choose one category to open its settings page.",
      workspace: "Settings",
    },
    descriptions: {
      account: "Who you are signed in as, and the name the app shows.",
      display: "Language, text size and motion. Text size and motion are saved in this browser.",
      workflow: "How a new case starts, and how the work is processed. Your choice is saved in this browser.",
      privacy: "Your password, where you are signed in, and what the app keeps.",
      help: "How the app is meant to be used.",
    },
    account: {
      name: "Display name",
      nameHint: "Shown in the app's menu. Not shown on reports.",
      nameEmpty: "Enter a name.",
      save: "Save name",
      saving: "Saving…",
      saved: "Name saved.",
      failed: "The name could not be saved. Try again.",
      email: "Email",
      workspace: "Workspace",
      workspaceValue: "Personal: only you can see your cases",
      fallbackName: "Workspace user",
      localOnly: "This copy of the app runs without real sign-in, so there is no account to change.",
      localName: "Demo Therapist",
    },
    display: {
      language: "Language",
      textSize: "Text size",
      standard: "Standard",
      large: "Large",
      motion: "Motion",
      followDevice: "Follow device",
      reduce: "Reduce",
      motionHint: "Reduce turns off the animations in the app even if your device allows them.",
    },
    workflow: {
      caseLanguage: "Language of a new case",
      caseLanguageHint: "Filled in when you create a case; you can change it on the form.",
      thai: "Thai",
      english: "English",
      facts: "How the work is processed",
      transcription: "Transcription",
      transcriptionExternal: "Recordings are sent to an external service to be transcribed",
      transcriptionLocal: "Recordings are transcribed on this deployment's server",
      review: "Review",
      reviewValue: "You check the transcript and the report before you use them",
      sharing: "Sharing",
      sharingValue: "A case belongs to you; it cannot be shared yet",
    },
    privacy: {
      passwordTitle: "Password",
      passwordBody: "Choose a new password for this account.",
      newPassword: "New password",
      confirmPassword: "Repeat the new password",
      passwordHint: (min) => `At least ${min} characters.`,
      tooShort: (min) => `Use at least ${min} characters.`,
      mismatch: "The two passwords are not the same.",
      samePassword: "Choose a password you have not used for this account.",
      change: "Change password",
      changing: "Changing…",
      changed: "Password changed.",
      failed: "The password could not be changed. Sign out, sign in again and retry.",
      everywhereTitle: "Sign out everywhere",
      everywhereBody: "Ends every session of this account, on this device and on any other, for example a shared computer.",
      everywhereButton: "Sign out everywhere",
      everywhereBusy: "Signing out…",
      everywhereFailed: "Could not sign out everywhere. Check your connection and try again.",
      localOnly: "This copy of the app runs without real sign-in, so there is no password to change.",
      dataTitle: "What the app keeps",
      dataLines: [
        ["Case records", "Codes, ages and notes you enter; no child's name is asked for"],
        ["Recordings", "Stored privately for transcription and playback"],
        ["Typed questions on the home screen", "Answered in your browser; not stored or sent"],
        ["This browser", "Your sign-in and the settings on this page"],
      ],
      privacyPage: "Read the full privacy page",
    },
    help: {
      lines: [
        ["Start", "On the home screen, choose a case and record or upload a session"],
        ["Transcript", "Correct the transcript and mark who is speaking before analysis"],
        ["Report", "A draft to review and edit; you decide what goes to families"],
        ["Clinical boundary", ""],
      ],
      privacyPage: "Privacy page",
    },
  },
  th: {
    page: {
      title: "ตั้งค่า",
      description: "บัญชีของคุณ การแสดงผลบนเครื่องนี้ และค่าเริ่มต้นของงานใหม่",
    },
    sections: {
      account: "บัญชี",
      display: "การแสดงผล",
      workflow: "การทำงาน",
      privacy: "ความปลอดภัยและข้อมูล",
      help: "ช่วยเหลือ",
    },
    nav: {
      label: "หมวดการตั้งค่า",
      allCategories: "หมวดการตั้งค่าทั้งหมด",
      choose: "เลือกหมวดเพื่อเปิดหน้าการตั้งค่า",
      workspace: "การตั้งค่า",
    },
    descriptions: {
      account: "บัญชีที่ใช้อยู่ และชื่อที่แอปแสดง",
      display: "ภาษา ขนาดตัวอักษร และการเคลื่อนไหว ขนาดตัวอักษรและการเคลื่อนไหวบันทึกไว้ในเบราว์เซอร์นี้",
      workflow: "ค่าเริ่มต้นของเคสใหม่ และวิธีประมวลผลงาน ตัวเลือกบันทึกไว้ในเบราว์เซอร์นี้",
      privacy: "รหัสผ่าน อุปกรณ์ที่ลงชื่อเข้าใช้ และข้อมูลที่แอปเก็บ",
      help: "วิธีใช้แอปตามที่ออกแบบไว้",
    },
    account: {
      name: "ชื่อที่แสดง",
      nameHint: "แสดงในเมนูของแอป ไม่แสดงในรายงาน",
      nameEmpty: "กรุณากรอกชื่อ",
      save: "บันทึกชื่อ",
      saving: "กำลังบันทึก…",
      saved: "บันทึกชื่อแล้ว",
      failed: "บันทึกชื่อไม่สำเร็จ ลองอีกครั้ง",
      email: "อีเมล",
      workspace: "พื้นที่ทำงาน",
      workspaceValue: "ส่วนตัว: มีเพียงคุณที่เห็นเคสของคุณ",
      fallbackName: "ผู้ใช้พื้นที่ทำงาน",
      localOnly: "แอปชุดนี้ทำงานโดยไม่มีการลงชื่อเข้าใช้จริง จึงไม่มีบัญชีให้แก้ไข",
      localName: "นักบำบัดทดลอง",
    },
    display: {
      language: "ภาษา",
      textSize: "ขนาดตัวอักษร",
      standard: "ปกติ",
      large: "ใหญ่",
      motion: "การเคลื่อนไหว",
      followDevice: "ตามอุปกรณ์",
      reduce: "ลดลง",
      motionHint: "เลือก \"ลดลง\" เพื่อปิดภาพเคลื่อนไหวในแอป แม้อุปกรณ์จะเปิดไว้",
    },
    workflow: {
      caseLanguage: "ภาษาของเคสใหม่",
      caseLanguageHint: "ใส่ให้ตอนสร้างเคส เปลี่ยนในแบบฟอร์มได้",
      thai: "ไทย",
      english: "อังกฤษ",
      facts: "วิธีประมวลผลงาน",
      transcription: "การถอดความ",
      transcriptionExternal: "ไฟล์เสียงถูกส่งไปถอดความที่บริการภายนอก",
      transcriptionLocal: "ไฟล์เสียงถูกถอดความบนเซิร์ฟเวอร์ของระบบนี้",
      review: "การตรวจทาน",
      reviewValue: "คุณตรวจบทถอดความและรายงานก่อนนำไปใช้",
      sharing: "การแชร์",
      sharingValue: "เคสเป็นของคุณ ยังแชร์ให้บัญชีอื่นไม่ได้",
    },
    privacy: {
      passwordTitle: "รหัสผ่าน",
      passwordBody: "ตั้งรหัสผ่านใหม่ของบัญชีนี้",
      newPassword: "รหัสผ่านใหม่",
      confirmPassword: "พิมพ์รหัสผ่านใหม่อีกครั้ง",
      passwordHint: (min) => `อย่างน้อย ${min} ตัวอักษร`,
      tooShort: (min) => `ใช้อย่างน้อย ${min} ตัวอักษร`,
      mismatch: "รหัสผ่านทั้งสองช่องไม่ตรงกัน",
      samePassword: "เลือกรหัสผ่านที่ไม่เคยใช้กับบัญชีนี้",
      change: "เปลี่ยนรหัสผ่าน",
      changing: "กำลังเปลี่ยน…",
      changed: "เปลี่ยนรหัสผ่านแล้ว",
      failed: "เปลี่ยนรหัสผ่านไม่สำเร็จ ลองออกจากระบบ เข้าสู่ระบบใหม่ แล้วลองอีกครั้ง",
      everywhereTitle: "ออกจากระบบทุกอุปกรณ์",
      everywhereBody: "ปิดทุกการลงชื่อเข้าใช้ของบัญชีนี้ ทั้งเครื่องนี้และเครื่องอื่น เช่น คอมพิวเตอร์ที่ใช้ร่วมกัน",
      everywhereButton: "ออกจากระบบทุกอุปกรณ์",
      everywhereBusy: "กำลังออกจากระบบ…",
      everywhereFailed: "ออกจากระบบทุกอุปกรณ์ไม่สำเร็จ ตรวจสอบการเชื่อมต่อแล้วลองอีกครั้ง",
      localOnly: "แอปชุดนี้ทำงานโดยไม่มีการลงชื่อเข้าใช้จริง จึงไม่มีรหัสผ่านให้เปลี่ยน",
      dataTitle: "ข้อมูลที่แอปเก็บ",
      dataLines: [
        ["ข้อมูลเคส", "รหัส อายุ และบันทึกที่คุณกรอก ไม่ถามชื่อเด็ก"],
        ["ไฟล์เสียง", "เก็บแบบส่วนตัวเพื่อถอดความและเปิดฟัง"],
        ["คำถามที่พิมพ์ในหน้าหลัก", "ตอบในเบราว์เซอร์ ไม่ถูกเก็บหรือส่งออกไป"],
        ["เบราว์เซอร์นี้", "การลงชื่อเข้าใช้ และการตั้งค่าในหน้านี้"],
      ],
      privacyPage: "อ่านหน้านโยบายความเป็นส่วนตัวฉบับเต็ม",
    },
    help: {
      lines: [
        ["เริ่มต้น", "ที่หน้าหลัก เลือกเคส แล้วอัดเสียงหรืออัปโหลดเซสชัน"],
        ["บทถอดความ", "แก้บทถอดความและระบุผู้พูดก่อนวิเคราะห์"],
        ["รายงาน", "เป็นฉบับร่างให้ตรวจและแก้ คุณเป็นผู้ตัดสินใจว่าจะส่งอะไรให้ครอบครัว"],
        ["ขอบเขตทางคลินิก", ""],
      ],
      privacyPage: "หน้านโยบายความเป็นส่วนตัว",
    },
  },
});
