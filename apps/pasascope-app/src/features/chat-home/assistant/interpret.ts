import { retypeOnOtherLayout } from "@/features/chat-home/assistant/keyboard-layout";

/**
 * What a typed line on the chat home is about. There is no language model: a
 * line is matched against fixed lists of words, in Thai and English, and each
 * topic has one prepared answer. A line that matches nothing is "unknown" and
 * is answered as such, never guessed at.
 */
export type AssistantIntent =
  | "greeting"
  | "capabilities"
  | "howto"
  | "today"
  | "pending"
  | "cases"
  | "findCase"
  | "newCase"
  | "record"
  | "upload"
  | "newSession"
  | "transcript"
  | "speakers"
  | "measures"
  | "reports"
  | "formats"
  | "privacy"
  | "consent"
  | "delete"
  | "diagnosis"
  | "language"
  | "settings"
  | "identity"
  | "thanks"
  | "bye";

export type Interpretation =
  /** `understoodAs` is set when the line only made sense on the other keyboard layout. */
  | { kind: "intent"; intent: AssistantIntent; understoodAs?: string }
  | { kind: "case"; query: string; understoodAs?: string }
  | { kind: "unknown" };

/** How well a line names one of the caller's cases. */
export type CaseMatch = "exact" | "partial" | "none";

type Rule = {
  intent: AssistantIntent;
  /**
   * 3: the line must not be mistaken for anything else (a diagnosis, a deletion).
   * 2: a named topic. 1: a general request. 0: small talk, only when nothing else fits.
   */
  rank: 0 | 1 | 2 | 3;
  /** Each pattern is a list of groups; it matches when every group has a term in the line. */
  patterns: string[][][];
};

const CASE_WORDS = ["เคส", "เด็ก", "คนไข้", "ผู้ป่วย", "case", "cases", "child", "children", "patient", "patients", "client", "clients"];
const SESSION_WORDS = ["เซสชัน", "เซสชั่น", "session", "sessions"];

const RULES: Rule[] = [
  {
    intent: "diagnosis",
    rank: 3,
    patterns: [[[
      "วินิจฉัย", "ออทิส", "ออทิซึม", "สมาธิสั้น", "ผิดปกติ", "ปกติไหม", "ปกติมั้ย", "ปกติหรือ", "พัฒนาการช้า", "พูดช้า",
      "เป็นโรค", "คัดกรอง",
      "diagnose", "diagnosis", "diagnostic", "autism", "autistic", "asd", "adhd", "disorder", "delayed", "delay",
      "screening", "screen for", "is my child normal", "normal",
    ]]],
  },
  {
    intent: "delete",
    rank: 3,
    patterns: [[[
      "ลบ", "ถอนความยินยอม", "ยกเลิกความยินยอม", "เพิกถอน", "ลบทิ้ง",
      "delete", "remove", "erase", "withdraw", "revoke",
    ]]],
  },
  {
    intent: "privacy",
    rank: 2,
    patterns: [
      [[
        "ความเป็นส่วนตัว", "ส่วนตัว", "ปลอดภัย", "ข้อมูลส่วนบุคคล", "เก็บข้อมูล", "ใครเห็น", "ใครดูได้", "ใครเข้าถึง",
        "เป็นความลับ", "รั่ว",
        "privacy", "private", "secure", "security", "safe", "pdpa", "gdpr", "confidential", "who can see", "who sees",
      ]],
      [
        ["เสียง", "ไฟล์", "ข้อมูล", "คลิป", "recording", "recordings", "audio", "data", "file", "files"],
        ["ไปไหน", "ไปที่ไหน", "อยู่ไหน", "อยู่ที่ไหน", "เก็บไว้", "เก็บที่", "ส่งไป", "where", "stored", "store", "kept", "keep", "sent"],
      ],
    ],
  },
  {
    intent: "consent",
    rank: 2,
    patterns: [[["ยินยอม", "ผู้ปกครองอนุญาต", "ขออนุญาต", "consent", "permission", "caregiver agree"]]],
  },
  {
    intent: "identity",
    rank: 2,
    patterns: [[[
      "คุณคือใคร", "เป็นใคร", "ชื่ออะไร", "เป็น ai", "เป็นเอไอ", "เอไอ", "เป็นบอท", "แชทบอท", "เป็นคนจริง", "เป็นคนหรือ",
      "ปัญญาประดิษฐ์", "ใช้ ai", "chatgpt", "gpt",
      "who are you", "what are you", "are you ai", "are you an ai", "are you a bot", "are you human", "are you real",
      "chatbot", "bot", "ai", "your name",
    ]]],
  },
  {
    intent: "today",
    rank: 2,
    patterns: [
      [
        ["วันนี้", "today", "todays", "today s", "tonight"],
        [
          ...CASE_WORDS, ...SESSION_WORDS, "งาน", "อะไรบ้าง", "ไรบ้าง", "ต้องทำ", "ตาราง", "คิว", "นัด",
          "schedule", "appointments", "work", "list", "have", "do i have", "anything",
        ],
      ],
    ],
  },
  {
    intent: "speakers",
    rank: 2,
    patterns: [[[
      "ผู้พูด", "คนพูด", "ใครพูด", "แยกเสียง", "แยกคนพูด", "เด็กหรือนักบำบัด",
      "speaker", "speakers", "diarization", "diarisation", "who is speaking", "who said", "unk",
    ]]],
  },
  {
    intent: "measures",
    rank: 2,
    patterns: [[[
      "ค่าชี้วัด", "ตัวชี้วัด", "ความยาวถ้อยความ", "ถ้อยความ", "จำนวนคำ", "วัดอะไร", "ผลวิเคราะห์", "วิเคราะห์",
      "ค่าทางภาษา", "ค่าภาษา",
      "mlu", "measure", "measures", "metric", "metrics", "mean length", "word count", "different words", "analysis",
      "analyse", "analyze", "statistics", "stats",
    ]]],
  },
  {
    intent: "formats",
    rank: 2,
    patterns: [[[
      "นามสกุล", "ไฟล์อะไร", "ไฟล์แบบไหน", "ไฟล์ประเภท", "ประเภทไฟล์", "ชนิดไฟล์", "รองรับไฟล์", "ไฟล์ที่รองรับ",
      "ขนาดไฟล์", "ไฟล์ใหญ่", "ใหญ่แค่ไหน", "ใหญ่สุด", "กี่ mb", "กี่เมก", "กี่เม็ก", "ยาวแค่ไหน", "ยาวสุด",
      "mp3", "wav", "m4a", "mp4", "webm", "ogg", "format", "formats", "file type", "file types", "file size",
      "size limit", "supported", "how big", "how large", "how long can", "max size", "maximum",
    ]]],
  },
  {
    intent: "reports",
    rank: 2,
    patterns: [[[
      "รายงาน", "ส่งออก", "พิมพ์รายงาน", "ดาวน์โหลด", "สรุปผล",
      "report", "reports", "pdf", "export", "print", "download", "summary",
    ]]],
  },
  {
    intent: "transcript",
    rank: 2,
    patterns: [[[
      "ถอดเสียง", "ถอดความ", "ถอดเทป", "ทรานสคริปต์", "บทถอด", "แก้คำ", "แก้ข้อความ", "แก้บท", "แม่นไหม", "แม่นยำ",
      "transcript", "transcripts", "transcription", "transcribe", "accuracy", "accurate",
    ]]],
  },
  {
    intent: "newCase",
    rank: 2,
    patterns: [[[
      "สร้างเคส", "เพิ่มเคส", "เคสใหม่", "เด็กใหม่", "เพิ่มเด็ก", "ลงทะเบียน", "คนไข้ใหม่",
      "new case", "add a case", "add case", "create a case", "create case", "new child", "add a child", "new patient",
      "register",
    ]]],
  },
  {
    intent: "findCase",
    rank: 2,
    patterns: [[[
      "เลือกเคส", "หาเคส", "ค้นหาเคส", "ค้นเคส", "เปิดเคส", "ค้นหาเด็ก", "หาเด็ก",
      "choose a case", "choose case", "find a case", "find case", "pick a case", "open a case", "search case",
      "search cases", "select a case", "look up a case",
    ]]],
  },
  {
    intent: "cases",
    rank: 1,
    patterns: [
      [["รายชื่อเคส", "เคสทั้งหมด", "ดูเคส", "เคสของฉัน", "my cases", "all cases", "case list", "list cases", "show cases"]],
      [
        CASE_WORDS,
        [
          "อะไร", "ไร", "ไหน", "ทั้งหมด", "กี่", "มี", "ดู", "รายชื่อ", "รายการ",
          "list", "all", "what", "which", "show", "how many", "my", "have", "see", "view",
        ],
      ],
    ],
  },
  {
    intent: "pending",
    rank: 1,
    patterns: [[[
      "งานค้าง", "ค้างอยู่", "ค้างไว้", "ทำค้าง", "ที่ค้าง", "ยังไม่เสร็จ", "ไม่เสร็จ", "ทำต่อ", "ต่อจากเดิม", "ทำอะไรต่อ",
      "เหลืออะไร", "ต้องทำอะไร", "รออยู่",
      "pending", "unfinished", "in progress", "left off", "leave off", "continue", "resume", "to do", "todo", "waiting",
      "outstanding", "what s next", "whats next", "what next", "next step",
    ]]],
  },
  {
    intent: "capabilities",
    rank: 1,
    patterns: [[[
      "ทำอะไรได้", "ทำไรได้", "ทำอะไรเป็น", "ทำไรเป็น", "ช่วยอะไรได้", "ช่วยไรได้", "ช่วยอะไร", "มีอะไรให้", "ความสามารถ",
      "ฟีเจอร์", "ถามอะไรได้", "ถามไรได้", "ช่วยด้วย", "ช่วยหน่อย", "ขอความช่วยเหลือ", "เมนู", "คำสั่ง", "ทำไรได้บ้าง",
      "what can you do", "what do you do", "what can i do", "what can i ask", "what can this do", "capabilities",
      "features", "help", "menu", "options", "commands",
    ]]],
  },
  {
    intent: "howto",
    rank: 1,
    patterns: [[[
      "ใช้ยังไง", "ใช้งานยังไง", "ใช้อย่างไร", "ใช้งานอย่างไร", "ใช้ไง", "ใช้งานไง", "ใช้ยังงัย", "วิธีใช้", "วิธีการใช้",
      "สอนใช้", "สอนวิธี", "สอนหน่อย", "เริ่มยังไง", "เริ่มต้นยังไง", "เริ่มตรงไหน", "เริ่มจากไหน", "เริ่มอย่างไร",
      "เริ่มต้นอย่างไร", "ทำยังไง", "ต้องทำยังไง", "ทำอย่างไร", "ขั้นตอน", "คู่มือ", "มือใหม่", "ใช้ไม่เป็น", "เพิ่งเริ่ม",
      "how to use", "how do i use", "how does it work", "how does this work", "how do i start", "how to start",
      "how do i begin", "get started", "getting started", "tutorial", "guide", "walkthrough", "instructions", "steps",
      "teach me", "show me how", "how it works", "i m new", "im new",
    ]]],
  },
  {
    intent: "record",
    rank: 1,
    patterns: [[[
      "อัดเสียง", "บันทึกเสียง", "อัดใหม่", "เริ่มอัด", "อัดคลิป", "ไมค์", "ไมโครโฟน",
      "record", "start recording", "record audio", "new recording", "mic", "microphone",
    ]]],
  },
  {
    intent: "upload",
    rank: 1,
    patterns: [[[
      "อัปโหลด", "อัพโหลด", "อับโหลด", "อัปไฟล์", "อัพไฟล์", "แนบไฟล์", "ส่งไฟล์", "ส่งเสียง", "เลือกไฟล์", "มีไฟล์",
      "ไฟล์เสียง", "นำเข้า",
      "upload", "attach", "send a file", "send file", "audio file", "import", "i have a file", "i have a recording",
    ]]],
  },
  {
    intent: "newSession",
    rank: 1,
    patterns: [[[
      "เซสชันใหม่", "เซสชั่นใหม่", "เริ่มเซสชัน", "เริ่มเซสชั่น", "เปิดเซสชัน", "สร้างเซสชัน", "เริ่มงานใหม่", "เริ่มใหม่",
      "new session", "start a session", "start session", "start a new session", "begin a session", "create a session",
    ]]],
  },
  {
    intent: "language",
    rank: 1,
    patterns: [[[
      "เปลี่ยนภาษา", "ภาษาอังกฤษ", "ภาษาไทย", "ภาษา",
      "english", "thai", "change language", "switch language", "language",
    ]]],
  },
  {
    intent: "settings",
    rank: 1,
    patterns: [[[
      "ตั้งค่า", "บัญชี", "โปรไฟล์", "รหัสผ่าน", "ออกจากระบบ", "ล็อกเอาท์", "ล็อกเอาต์",
      "settings", "setting", "account", "profile", "password", "log out", "logout", "sign out",
    ]]],
  },
  {
    intent: "thanks",
    rank: 0,
    patterns: [[["ขอบคุณ", "ขอบใจ", "แต๊ง", "thank", "thanks", "thank you", "thx", "ty", "cheers", "appreciate"]]],
  },
  {
    intent: "bye",
    rank: 0,
    patterns: [[["ลาก่อน", "บาย", "ไปก่อน", "เจอกัน", "ราตรีสวัสดิ์", "bye", "goodbye", "see you", "good night"]]],
  },
  {
    intent: "greeting",
    rank: 0,
    patterns: [[[
      "สวัสดี", "หวัดดี", "ดีครับ", "ดีค่ะ", "ดีคับ", "ดีจ้า", "ฮัลโหล", "ฮัลโล", "เฮลโล", "อรุณสวัสดิ์",
      "hello", "hi", "hey", "hiya", "good morning", "good afternoon", "good evening", "greetings",
    ]]],
  },
];

/**
 * Lower case, no punctuation, single spaces, and a letter held down ("helloooo",
 * "สวัสดีีีี") cut back to one. Polite particles and filler words stay: terms
 * are found anywhere in the line, so what surrounds them does not matter.
 */
export function normalize(raw: string): string {
  return raw
    .normalize("NFC")
    .toLowerCase()
    .replace(/[​-‍﻿]/g, "")
    .replace(/ๆ/g, "")
    .replace(/(.)\1{2,}/gu, "$1")
    .replace(/[^\p{L}\p{M}\p{N}]+/gu, " ")
    .trim();
}

const ASCII_TERM = /^[a-z0-9 ]+$/;
const asciiMatchers = new Map<string, RegExp>();

/** Thai has no spaces, so a Thai term is found anywhere; an English one must stand as whole words. */
function has(line: string, term: string): boolean {
  if (!ASCII_TERM.test(term)) return line.includes(term);
  let matcher = asciiMatchers.get(term);
  if (!matcher) {
    matcher = new RegExp(`(?<![a-z0-9])${term}(?![a-z0-9])`);
    asciiMatchers.set(term, matcher);
  }
  return matcher.test(line);
}

/** The length of the terms a pattern matched, so the more specific of two rules wins. */
function weigh(line: string, pattern: string[][]): number {
  let weight = 0;
  for (const group of pattern) {
    let best = 0;
    for (const term of group) {
      if (term.length > best && has(line, term)) best = term.length;
    }
    if (best === 0) return 0;
    weight += best;
  }
  return weight;
}

function matchIntent(line: string): AssistantIntent | null {
  let winner: AssistantIntent | null = null;
  let winningScore = 0;
  for (const rule of RULES) {
    const weight = Math.max(...rule.patterns.map((pattern) => weigh(line, pattern)));
    if (weight === 0) continue;
    const score = rule.rank * 1000 + weight;
    if (score > winningScore) {
      winner = rule.intent;
      winningScore = score;
    }
  }
  return winner;
}

function interpretLine(raw: string, matchCase: (query: string) => CaseMatch): Interpretation {
  const query = raw.trim();
  // A line that is exactly a case's name or code is that case, whatever words it contains.
  if (matchCase(query) === "exact") return { kind: "case", query };
  const intent = matchIntent(normalize(raw));
  if (intent) return { kind: "intent", intent };
  if (matchCase(query) === "partial") return { kind: "case", query };
  return { kind: "unknown" };
}

export function interpret(raw: string, matchCase: (query: string) => CaseMatch = () => "none"): Interpretation {
  const direct = interpretLine(raw, matchCase);
  if (direct.kind !== "unknown") return direct;
  const retyped = retypeOnOtherLayout(raw).trim();
  if (!retyped || retyped === raw.trim()) return direct;
  const second = interpretLine(retyped, matchCase);
  return second.kind === "unknown" ? second : { ...second, understoodAs: retyped };
}
