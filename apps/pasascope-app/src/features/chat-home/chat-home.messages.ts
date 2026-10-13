import type { HomeSessionStage } from "@/features/chat-home/chat-home-model";
import { defineMessages } from "@/i18n/messages";

type ChatHomeCopy = {
  greeting: string;
  lead: string;
  threadLabel: string;
  cards: {
    record: { title: string; body: string };
    upload: { title: string; body: string };
    resume: { title: string; none: string };
  };
  composer: {
    label: string;
    placeholder: string;
    submit: string;
    attach: string;
    chooseCase: string;
  };
  /** Questions offered under the greeting; pressing one asks it. */
  suggestions: { capabilities: string; howto: string; today: string };
  recent: {
    title: string;
    trigger: string;
    searchLabel: string;
    searchPlaceholder: string;
    empty: string;
    noMatch: string;
    loading: string;
    failed: string;
    retry: string;
    newSession: string;
  };
  /** What a session is waiting for, as shown on a recent-session row. */
  stage: Record<HomeSessionStage, string>;
  start: {
    intents: { recording: string; audio: string; findCase: string; newSession: string };
    askCase: string;
    askCaseFiltered: (query: string) => string;
    noCases: string;
    noMatch: (query: string) => string;
    more: (count: number) => string;
    newCase: string;
    newCaseFrom: (name: string) => string;
    consentNeeded: string;
    askNewCase: string;
    caseCode: string;
    nickname: string;
    nicknameHint: string;
    ageYears: string;
    ageMonths: string;
    ageRequired: string;
    codeRequired: string;
    createCase: string;
    creatingCase: string;
    createFailed: string;
    cancel: string;
    askIntent: (caseLabel: string) => string;
    openCase: string;
    askConsent: string;
    confirmConsent: string;
    consentFailed: string;
    opening: string;
    openFailed: string;
    startOver: string;
    attached: (filename: string) => string;
  };
};

export const chatHomeMessages = defineMessages<ChatHomeCopy>({
  en: {
    greeting: "What would you like to do today?",
    lead: "Send a recording of the child and PasaScope will take you through it step by step.",
    threadLabel: "Starting a session",
    cards: {
      record: { title: "Record new audio", body: "Record the session on this device" },
      upload: { title: "Upload an audio file", body: "Transcribe a recording you already have" },
      resume: { title: "Pick up where you left off", none: "Nothing waiting" },
    },
    composer: {
      label: "Ask PasaScope or find a case",
      placeholder: "Ask how it works, or type a case name…",
      submit: "Send",
      attach: "Attach audio file",
      chooseCase: "Choose a case",
    },
    suggestions: {
      capabilities: "What can you do?",
      howto: "How do I use it?",
      today: "What do I have today?",
    },
    recent: {
      title: "Recent sessions",
      trigger: "Recent sessions",
      searchLabel: "Search sessions",
      searchPlaceholder: "Search…",
      empty: "No sessions yet. Your sessions will appear here.",
      noMatch: "No session matches that search.",
      loading: "Loading sessions…",
      failed: "Sessions could not be loaded.",
      retry: "Try again",
      newSession: "Start a new session",
    },
    stage: {
      audio: "Waiting for audio",
      processing: "Transcribing",
      failed: "Transcription failed",
      transcript: "Transcript to check",
      measures: "Measures ready",
      report: "Report draft ready",
    },
    start: {
      intents: {
        recording: "Record new audio",
        audio: "Upload an audio file",
        findCase: "Choose a case",
        newSession: "Start a new session",
      },
      askCase: "Which case is this session for?",
      askCaseFiltered: (query) => `Cases matching “${query}”. Which one is this session for?`,
      noCases: "There are no cases yet. Create the first one to begin.",
      noMatch: (query) => `No case matches “${query}”.`,
      more: (count) => `${count} more. Type a name or code to find another case.`,
      newCase: "New case",
      newCaseFrom: (name) => `Create a new case called “${name}”`,
      consentNeeded: "Consent not confirmed yet",
      askNewCase: "A few details for the new case. Use a code or nickname, never the child's full name.",
      caseCode: "Case code",
      nickname: "Nickname",
      nicknameHint: "Optional and de-identified",
      ageYears: "Age: years",
      ageMonths: "Age: months",
      ageRequired: "Enter the child's age.",
      codeRequired: "Enter a case code.",
      createCase: "Create case",
      creatingCase: "Saving case…",
      createFailed: "The case could not be created. Check the details and try again.",
      cancel: "Cancel",
      askIntent: (caseLabel) => `What would you like to do for ${caseLabel}?`,
      openCase: "Open the case page",
      askConsent: "Before any audio is collected, confirm the caregiver's consent.",
      confirmConsent: "Confirm and continue",
      consentFailed: "Consent could not be saved. Try again.",
      opening: "Opening the session…",
      openFailed: "The session could not be opened. Try again.",
      startOver: "Start over",
      attached: (filename) => `Audio file: ${filename}`,
    },
  },
  th: {
    greeting: "วันนี้ให้ช่วยอะไรดี",
    lead: "ส่งเสียงของเด็กมา แล้ว PasaScope จะพาทำทีละขั้น",
    threadLabel: "การเริ่มเซสชัน",
    cards: {
      record: { title: "บันทึกเสียงใหม่", body: "อัดเสียงเซสชันจากเครื่องนี้" },
      upload: { title: "อัปโหลดไฟล์เสียง", body: "ถอดเสียงจากไฟล์ที่มีอยู่" },
      resume: { title: "ทำงานที่ค้างต่อ", none: "ยังไม่มีงานค้าง" },
    },
    composer: {
      label: "ถาม PasaScope หรือค้นหาเคส",
      placeholder: "ถามวิธีใช้ หรือพิมพ์ชื่อเคส…",
      submit: "ส่ง",
      attach: "แนบไฟล์เสียง",
      chooseCase: "เลือกเคส",
    },
    suggestions: {
      capabilities: "ทำอะไรได้บ้าง",
      howto: "ใช้งานยังไง",
      today: "วันนี้มีอะไรบ้าง",
    },
    recent: {
      title: "เซสชันล่าสุด",
      trigger: "เซสชันล่าสุด",
      searchLabel: "ค้นหาเซสชัน",
      searchPlaceholder: "ค้นหา…",
      empty: "ยังไม่มีเซสชัน เซสชันของคุณจะแสดงที่นี่",
      noMatch: "ไม่พบเซสชันที่ตรงกับคำค้น",
      loading: "กำลังโหลดเซสชัน…",
      failed: "โหลดเซสชันไม่สำเร็จ",
      retry: "ลองอีกครั้ง",
      newSession: "เริ่มเซสชันใหม่",
    },
    stage: {
      audio: "รอส่งเสียง",
      processing: "กำลังถอดเสียง",
      failed: "ถอดเสียงไม่สำเร็จ",
      transcript: "รอตรวจบทถอดเสียง",
      measures: "มีค่าทางภาษาแล้ว",
      report: "ร่างรายงานพร้อม",
    },
    start: {
      intents: {
        recording: "บันทึกเสียงใหม่",
        audio: "อัปโหลดไฟล์เสียง",
        findCase: "เลือกเคส",
        newSession: "เริ่มเซสชันใหม่",
      },
      askCase: "เซสชันนี้เป็นของเคสไหน",
      askCaseFiltered: (query) => `เคสที่ตรงกับ “${query}” เซสชันนี้เป็นของเคสไหน`,
      noCases: "ยังไม่มีเคส สร้างเคสแรกเพื่อเริ่มได้เลย",
      noMatch: (query) => `ไม่พบเคสที่ตรงกับ “${query}”`,
      more: (count) => `อีก ${count} เคส พิมพ์ชื่อหรือรหัสเพื่อค้นหา`,
      newCase: "เคสใหม่",
      newCaseFrom: (name) => `สร้างเคสใหม่ชื่อ “${name}”`,
      consentNeeded: "ยังไม่ได้ยืนยันความยินยอม",
      askNewCase: "ขอข้อมูลของเคสใหม่สั้น ๆ ใช้รหัสหรือชื่อเล่น ไม่ใช้ชื่อ-นามสกุลจริงของเด็ก",
      caseCode: "รหัสเคส",
      nickname: "ชื่อเรียก",
      nicknameHint: "ไม่บังคับ และต้องไม่ระบุตัวตน",
      ageYears: "อายุ (ปี)",
      ageMonths: "อายุ (เดือน)",
      ageRequired: "กรุณาใส่อายุของเด็ก",
      codeRequired: "กรุณาใส่รหัสเคส",
      createCase: "สร้างเคส",
      creatingCase: "กำลังบันทึกเคส…",
      createFailed: "สร้างเคสไม่ได้ ตรวจรายละเอียดแล้วลองอีกครั้ง",
      cancel: "ยกเลิก",
      askIntent: (caseLabel) => `จะทำอะไรกับเคส ${caseLabel}`,
      openCase: "เปิดหน้าเคส",
      askConsent: "ก่อนเก็บเสียง ต้องยืนยันความยินยอมของผู้ปกครองก่อน",
      confirmConsent: "ยืนยันและไปต่อ",
      consentFailed: "บันทึกความยินยอมไม่สำเร็จ ลองอีกครั้ง",
      opening: "กำลังเปิดเซสชัน…",
      openFailed: "เปิดเซสชันไม่สำเร็จ ลองอีกครั้ง",
      startOver: "เริ่มใหม่",
      attached: (filename) => `ไฟล์เสียง: ${filename}`,
    },
  },
});
