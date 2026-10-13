import { describe, expect, it } from "vitest";

import { interpret, normalize, type AssistantIntent, type CaseMatch } from "@/features/chat-home/assistant/interpret";
import { retypeOnOtherLayout } from "@/features/chat-home/assistant/keyboard-layout";

/** Lines a therapist might type, by the topic each must land on. Add a line here when one is missed. */
const PHRASES: Record<AssistantIntent, string[]> = {
  greeting: ["สวัสดี", "สวัสดีครับ", "สวัสดีค่ะะะ", "หวัดดีจ้า", "ดีครับ", "ฮัลโหล", "hello", "Hi!", "hey there", "Good morning", "helloooo"],
  capabilities: [
    "ทำอะไรได้บ้าง", "ทำไรได้บ้างครับ", "คุณทำอะไรได้", "ช่วยอะไรได้บ้างคะ", "มีฟีเจอร์อะไรบ้าง", "ถามอะไรได้บ้าง", "ช่วยด้วย",
    "ขอดูเมนูหน่อย", "what can you do", "What can you do?", "what can I ask you", "help", "Help me please",
    "show me the features", "what do you do",
  ],
  howto: [
    "ใช้ยังไง", "ใช้งานยังไงครับ", "ใช้อย่างไร", "สอนวิธีใช้หน่อย", "ช่วยสอนใช้งานหน่อยค่ะ", "เริ่มยังไงดี", "เริ่มตรงไหน",
    "ต้องทำยังไงบ้าง", "ขอขั้นตอนหน่อย", "มีคู่มือไหม", "มือใหม่ครับ", "ใช้ไม่เป็น", "how to use this", "How do I use PasaScope?",
    "how does it work", "how do I start", "getting started", "tutorial please", "I'm new here", "show me how",
  ],
  today: [
    "วันนี้มีเคสอะไรบ้าง", "วันนี้มีเคสไหม", "มีเคสอะไรบ้างวันนี้", "วันนี้มีงานอะไรบ้างครับ", "เซสชันวันนี้", "วันนี้ต้องทำอะไร",
    "วันนี้มีอะไรบ้าง", "what cases do I have today", "today's sessions", "any cases today?", "what is on my schedule today",
    "do I have anything today",
  ],
  pending: [
    "มีงานค้างไหม", "งานค้างมีอะไรบ้าง", "อะไรยังไม่เสร็จ", "ทำต่อจากเดิม", "ต้องทำอะไรต่อ", "เหลืออะไรอีกบ้าง",
    "what's pending", "anything unfinished?", "where did I leave off", "continue where I left off", "what's next",
    "my to do list",
  ],
  cases: [
    "มีเคสอะไรบ้าง", "เคสทั้งหมด", "ขอดูรายชื่อเคส", "มีเด็กกี่คน", "ดูเคสของฉัน", "มีเคสไหนบ้าง", "show my cases",
    "list all cases", "what cases do I have", "how many children do I have", "which patients",
  ],
  findCase: ["เลือกเคส", "หาเคสหน่อย", "ค้นหาเคส", "อยากเปิดเคส", "choose a case", "find a case", "open a case", "search cases"],
  newCase: [
    "สร้างเคสใหม่", "เพิ่มเคส", "เคสใหม่ครับ", "เพิ่มเด็กใหม่", "ลงทะเบียนเด็ก", "new case", "add a case", "create a case",
    "add a child", "register a new patient",
  ],
  record: [
    "อัดเสียง", "อยากอัดเสียงใหม่", "บันทึกเสียงเด็ก", "เริ่มอัดเลย", "อัดเสียงยังไง", "ใช้ไมค์", "record", "start recording",
    "I want to record audio", "new recording", "use the microphone",
  ],
  upload: [
    "อัปโหลดไฟล์", "อัพโหลดเสียง", "อยากอัพไฟล์", "แนบไฟล์เสียง", "มีไฟล์อยู่แล้ว", "ส่งไฟล์เสียง", "upload", "upload a file",
    "I have a recording", "attach an audio file", "import audio",
  ],
  newSession: ["เริ่มเซสชันใหม่", "เซสชันใหม่", "เปิดเซสชั่นใหม่", "new session", "start a new session", "Start session"],
  transcript: [
    "ถอดเสียงยังไง", "ถอดเสียงแม่นไหม", "แก้ข้อความที่ถอดผิดยังไง", "ทรานสคริปต์อยู่ไหน", "how does transcription work",
    "is the transcript accurate", "edit the transcript", "transcribe",
  ],
  speakers: [
    "กำหนดผู้พูดยังไง", "ผู้พูดคือใคร", "แยกเสียงเด็กกับนักบำบัดได้ไหม", "ใครพูดบรรทัดไหน", "ทำไมเป็น UNK",
    "how do I set speakers", "assign a speaker", "who is speaking", "speaker labels",
  ],
  measures: [
    "ค่าชี้วัดภาษาคืออะไร", "MLU คืออะไร", "วัดอะไรบ้าง", "ความยาวถ้อยความเฉลี่ย", "ผลวิเคราะห์มีอะไรบ้าง", "นับจำนวนคำไหม",
    "what is MLU", "which measures do you compute", "language metrics", "what does the analysis show",
  ],
  reports: [
    "รายงานอยู่ไหน", "ขอดูรายงาน", "ส่งออกรายงานยังไง", "พิมพ์รายงานได้ไหม", "ดาวน์โหลด PDF", "รายงานทำยังไง",
    "where are my reports", "export the report", "can I print it", "download pdf", "show reports",
  ],
  formats: [
    "รองรับไฟล์อะไรบ้าง", "ไฟล์แบบไหนได้บ้าง", "ใช้ mp3 ได้ไหม", "ขนาดไฟล์สูงสุดเท่าไหร่", "ไฟล์ใหญ่ได้แค่ไหน", "นามสกุลไฟล์",
    "what file types are supported", "is wav ok", "file size limit", "how big can the file be", "supported formats",
  ],
  privacy: [
    "เสียงไปไหน", "ไฟล์เสียงเก็บไว้ที่ไหน", "ข้อมูลปลอดภัยไหม", "ใครเห็นข้อมูลได้บ้าง", "ความเป็นส่วนตัว", "ข้อมูลเด็กส่งไปที่ไหน",
    "is it secure", "where is the recording stored", "who can see my data", "privacy policy", "is my data safe",
    "where does the audio go",
  ],
  consent: [
    "ทำไมต้องขอความยินยอม", "ความยินยอมผู้ปกครอง", "ต้องให้ผู้ปกครองอนุญาตไหม", "why do you need consent",
    "caregiver consent", "do I need permission",
  ],
  delete: [
    "ลบเคสยังไง", "ลบไฟล์เสียง", "อยากลบข้อมูล", "ลบเคสทั้งหมด", "ถอนความยินยอม", "ลบรายงาน", "delete a case",
    "how do I delete my data", "remove the recording", "erase everything", "withdraw consent", "delete all cases",
  ],
  diagnosis: [
    "วินิจฉัยได้ไหม", "เด็กเป็นออทิสติกไหม", "ช่วยวินิจฉัยหน่อย", "ลูกพูดช้าผิดปกติไหม", "ผลปกติไหม", "คัดกรองออทิสติก",
    "can you diagnose", "does my child have autism", "is this normal", "ASD screening", "is the child delayed",
  ],
  language: ["เปลี่ยนภาษา", "ขอภาษาอังกฤษ", "ใช้ภาษาไทยได้ไหม", "English please", "switch language", "change the language", "Thai"],
  settings: [
    "ตั้งค่าอยู่ไหน", "เปลี่ยนรหัสผ่าน", "ออกจากระบบ", "แก้โปรไฟล์", "settings", "change my password", "log out",
    "my account", "sign out",
  ],
  identity: [
    "คุณคือใคร", "เป็น AI ไหม", "นี่เป็นบอทหรือเปล่า", "คุณชื่ออะไร", "ใช้ ChatGPT เหรอ", "who are you", "are you an AI",
    "are you a bot", "am I talking to a chatbot", "what's your name",
  ],
  thanks: ["ขอบคุณ", "ขอบคุณครับ", "ขอบใจนะ", "thanks", "Thank you!", "thx", "cheers"],
  bye: ["ลาก่อน", "บายครับ", "ไปก่อนนะ", "bye", "Goodbye", "see you"],
};

const UNKNOWN = [
  "อากาศวันนี้เป็นไง", "กินข้าวหรือยัง", "ราคาหุ้น", "asdfgh", "tell me a joke", "what is the capital of France",
  "12345", "…", "น้องมะลิ", "the weather",
];

describe("normalize", () => {
  it("drops case, punctuation and held-down letters", () => {
    expect(normalize("  Helloooo!!  ")).toBe("hello");
    expect(normalize("สวัสดีีีีี ค่ะ??")).toBe("สวัสดี ค่ะ");
    expect(normalize("What's next?")).toBe("what s next");
    expect(normalize("ช้าๆ")).toBe("ช้า");
  });
});

describe("interpret", () => {
  for (const [intent, lines] of Object.entries(PHRASES) as Array<[AssistantIntent, string[]]>) {
    it.each(lines)(`reads "%s" as ${intent}`, (line) => {
      expect(interpret(line)).toEqual({ kind: "intent", intent });
    });
  }

  it.each(UNKNOWN)('does not guess at "%s"', (line) => {
    expect(interpret(line)).toEqual({ kind: "unknown" });
  });

  it("does not find an English word inside another word", () => {
    // "hi" in "this", "ai" in "said", "bot" in "both", "record" in "records".
    expect(interpret("this said both")).toEqual({ kind: "unknown" });
  });

  it("reads a line typed on the other keyboard layout, and says how it read it", () => {
    // "ทำไรได้บ้าง" typed with the keyboard left on English.
    expect(interpret("mewiwfh[hk'")).toEqual({ kind: "intent", intent: "capabilities", understoodAs: "ทำไรได้บ้าง" });
    // "help" typed with the keyboard left on Thai.
    expect(interpret("้ำสย")).toEqual({ kind: "intent", intent: "capabilities", understoodAs: "help" });
    expect(retypeOnOtherLayout("9voouh")).toBe("ตอนนี้");
  });

  describe("with the caller's cases", () => {
    const names = ["Tonkla", "PS-0142", "น้องรายงาน"];
    const matchCase = (query: string): CaseMatch => {
      const needle = query.trim().toLowerCase();
      if (!needle) return "none";
      if (names.some((name) => name.toLowerCase() === needle)) return "exact";
      return names.some((name) => name.toLowerCase().includes(needle)) ? "partial" : "none";
    };

    it("takes a case's name or code as that case", () => {
      expect(interpret("tonk", matchCase)).toEqual({ kind: "case", query: "tonk" });
      expect(interpret("PS-0142", matchCase)).toEqual({ kind: "case", query: "PS-0142" });
    });

    it("takes an exact case name as the case even when it contains a topic word", () => {
      expect(interpret("น้องรายงาน", matchCase)).toEqual({ kind: "case", query: "น้องรายงาน" });
      expect(interpret("รายงานอยู่ไหน", matchCase)).toEqual({ kind: "intent", intent: "reports" });
    });

    it("finds a case name typed on the other layout", () => {
      // "Tonkla" typed with the keyboard left on Thai.
      expect(interpret(retypeOnOtherLayout("Tonkla"), matchCase)).toEqual({
        kind: "case",
        query: "Tonkla",
        understoodAs: "Tonkla",
      });
    });
  });
});
