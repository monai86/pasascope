import type { AssistantIntent } from "@/features/chat-home/assistant/interpret";
import { defineMessages } from "@/i18n/messages";

/** A question the assistant offers as a button; pressing it asks that question. */
export type AskTopic =
  | "capabilities"
  | "howto"
  | "today"
  | "pending"
  | "cases"
  | "transcript"
  | "speakers"
  | "measures"
  | "reports"
  | "formats"
  | "privacy"
  | "diagnosis";

/** Topics whose answer is the same every time. */
export type FixedTopic = Exclude<
  AssistantIntent,
  // Answered from the caller's sessions and cases.
  | "today" | "pending" | "cases" | "reports"
  // Open the start-session conversation instead of answering.
  | "record" | "upload" | "newSession" | "findCase" | "newCase"
>;

type AssistantCopy = {
  threadLabel: string;
  /** Read to assistive technology while the answer is on its way. */
  typing: string;
  understoodAs: (text: string) => string;
  clear: string;
  loading: string;
  failed: string;
  retry: string;
  ask: Record<AskTopic, string>;
  links: { cases: string; reports: string; privacy: string; settings: string };
  languages: { th: string; en: string };
  searchFor: (text: string) => string;
  fixed: Record<FixedTopic, { lines: string[]; steps?: string[] }>;
  today: {
    some: (count: number) => string;
    none: string;
    noSchedule: string;
    pendingToo: (count: number) => string;
  };
  pending: { some: (count: number) => string; none: string; noSessions: string };
  cases: { some: (count: number) => string; none: string; more: (count: number) => string };
  reports: { about: string; ready: (count: number) => string; none: string };
  unknown: { lines: string[] };
};

export const assistantMessages = defineMessages<AssistantCopy>({
  en: {
    threadLabel: "Questions and answers",
    typing: "PasaScope is answering…",
    understoodAs: (text) => `Read as “${text}”: the keyboard was set to the other language.`,
    clear: "Back to the start",
    loading: "Loading your sessions and cases…",
    failed: "Your sessions and cases could not be loaded.",
    retry: "Try again",
    ask: {
      capabilities: "What can you do?",
      howto: "How do I use it?",
      today: "What do I have today?",
      pending: "What is unfinished?",
      cases: "Show my cases",
      transcript: "How does transcription work?",
      speakers: "How do I set speakers?",
      measures: "What are the language measures?",
      reports: "Where are my reports?",
      formats: "Which audio files work?",
      privacy: "Where does the audio go?",
      diagnosis: "Does it diagnose?",
    },
    links: {
      cases: "Open Cases",
      reports: "Open Reports",
      privacy: "Read the privacy page",
      settings: "Open Settings",
    },
    languages: { th: "ไทย", en: "English" },
    searchFor: (text) => `Look for “${text}” in cases`,
    fixed: {
      greeting: {
        lines: ["Hello. Ask about using PasaScope, or type a case name to find it."],
      },
      capabilities: {
        lines: [
          "PasaScope takes a recording of a child's session through to a report:",
          "This field answers a prepared set of questions about using PasaScope. It is not an AI that can talk about anything.",
        ],
        steps: [
          "Record the session, or upload an audio file",
          "Transcribe it into text for you to check and correct",
          "Mark each line as the child or the therapist",
          "Work out language measures such as mean length of utterance (MLU)",
          "Draft a report you can edit, export and print",
        ],
      },
      howto: {
        lines: ["One session takes five steps:", "Each step has a button in the conversation. Start with one of these."],
        steps: [
          "Choose a case, or create a new one",
          "Confirm the caregiver's consent",
          "Record, or upload an audio file",
          "Check the transcript and set the speaker of each line",
          "Look at the language measures, then draft the report",
        ],
      },
      transcript: {
        lines: [
          "After you send audio, PasaScope transcribes it into lines of text with their times.",
          "The transcript is a machine draft and can be wrong, most of all with a child's speech. Check every line before you rely on it.",
          "On the session's transcript page you can correct the text, split a line and play one line at a time.",
        ],
      },
      speakers: {
        lines: ["You decide who said each line, on the session's transcript page. A line with no speaker yet shows as UNK."],
        steps: [
          "Press Child or Therapist on a line. The next line with no speaker is selected for you.",
          "From the keyboard: arrows choose a line, 1 is Child, 2 is Therapist, Space plays the line.",
          "When two people speak in one line, put the cursor where it should break and press Ctrl+Enter.",
          "You can set every line with no speaker to one person at once, then change the exceptions.",
        ],
      },
      measures: {
        lines: [
          "PasaScope works these out from the child's utterances in the transcript: mean length of utterance (MLU), total words and different words.",
          "They are descriptive observations, not a judgement or a diagnosis.",
          "If the transcript changes afterwards, the measures have to be taken again.",
        ],
      },
      formats: {
        lines: [
          "Audio files in WAV, MP3, M4A, MP4, WebM and OGG work.",
          "When transcription runs on an outside service, a file can be up to 25 MB. A larger one is stopped before it is uploaded.",
        ],
      },
      privacy: {
        lines: [
          "Your records are in your own workspace. No other user can open them.",
          "When transcription runs on an outside service, the recording is sent to it. PasaScope says so before you send.",
          "Use a code or nickname for the child, never the full name.",
          "Withdrawing a case's consent removes that case's recordings.",
        ],
      },
      consent: {
        lines: [
          "The caregiver's consent is confirmed before any audio is collected. A session cannot be created without it.",
          "It is confirmed once for each case.",
          "Consent can be withdrawn on the case's page, which removes that case's recordings.",
        ],
      },
      delete: {
        lines: [
          "Nothing can be deleted from this field, so that nothing is deleted by a mistyped line.",
          "To remove a case's recordings, withdraw its consent on the case's page.",
          "To delete your whole account with everything in it, go to Settings › Privacy & Security.",
        ],
      },
      diagnosis: {
        lines: [
          "PasaScope does not diagnose, and does not say whether a child is typical or not.",
          "It transcribes a language sample and summarises measures from it. Interpreting them is for the speech-language therapist.",
          "It has not been clinically validated for Thai.",
        ],
      },
      language: { lines: ["Choose the language of the interface."] },
      settings: {
        lines: ["Log out with the button beside your name in the navigation. Everything else is on the Settings page."],
      },
      identity: {
        lines: [
          "This is PasaScope's guide. It is not an AI and not a person.",
          "It matches the words you type to prepared answers, so it can only help with using PasaScope.",
        ],
      },
      thanks: { lines: ["You're welcome. Ask again any time."] },
      bye: { lines: ["Goodbye. Your sessions are where you left them."] },
    },
    today: {
      some: (count) => (count === 1 ? "There is 1 session dated today." : `There are ${count} sessions dated today.`),
      none: "No session is dated today.",
      noSchedule: "PasaScope has no appointment calendar, so this shows your recent sessions dated today.",
      pendingToo: (count) =>
        count === 1 ? "1 earlier session is still unfinished." : `${count} earlier sessions are still unfinished.`,
    },
    pending: {
      some: (count) => (count === 1 ? "1 session is unfinished." : `${count} sessions are unfinished.`),
      none: "Nothing is unfinished. Every recent session has a report draft.",
      noSessions: "There are no sessions yet.",
    },
    cases: {
      some: (count) => (count === 1 ? "You have 1 case." : `You have ${count} cases.`),
      none: "There are no cases yet.",
      more: (count) => `${count} more on the Cases page.`,
    },
    reports: {
      about: "A report is drafted from a session's language measures. You can edit, export and print it.",
      ready: (count) => (count === 1 ? "1 recent session has a report draft." : `${count} recent sessions have a report draft.`),
      none: "No recent session has a report draft yet.",
    },
    unknown: {
      lines: [
        "PasaScope did not understand that.",
        "This field answers questions about using PasaScope. Try a shorter question, or pick one of these.",
      ],
    },
  },
  th: {
    threadLabel: "ถามตอบ",
    typing: "PasaScope กำลังตอบ…",
    understoodAs: (text) => `อ่านว่า “${text}” เพราะแป้นพิมพ์อยู่ผิดภาษา`,
    clear: "กลับไปหน้าเริ่มต้น",
    loading: "กำลังโหลดเซสชันและเคสของคุณ…",
    failed: "โหลดเซสชันและเคสของคุณไม่สำเร็จ",
    retry: "ลองอีกครั้ง",
    ask: {
      capabilities: "ทำอะไรได้บ้าง",
      howto: "ใช้งานยังไง",
      today: "วันนี้มีอะไรบ้าง",
      pending: "มีงานค้างไหม",
      cases: "ดูเคสของฉัน",
      transcript: "ถอดเสียงทำงานยังไง",
      speakers: "กำหนดผู้พูดยังไง",
      measures: "ค่าทางภาษาคืออะไร",
      reports: "รายงานอยู่ที่ไหน",
      formats: "ใช้ไฟล์เสียงแบบไหนได้",
      privacy: "เสียงถูกส่งไปที่ไหน",
      diagnosis: "วินิจฉัยได้ไหม",
    },
    links: {
      cases: "เปิดหน้าเคส",
      reports: "เปิดหน้ารายงาน",
      privacy: "อ่านหน้าความเป็นส่วนตัว",
      settings: "เปิดหน้าตั้งค่า",
    },
    languages: { th: "ไทย", en: "English" },
    searchFor: (text) => `ค้นหา “${text}” ในเคส`,
    fixed: {
      greeting: {
        lines: ["สวัสดี ถามเรื่องการใช้งาน PasaScope ได้เลย หรือพิมพ์ชื่อเคสเพื่อค้นหา"],
      },
      capabilities: {
        lines: [
          "PasaScope พาเสียงของเด็กหนึ่งเซสชันไปจนถึงรายงาน:",
          "ช่องนี้ตอบคำถามเรื่องการใช้งาน PasaScope ตามหัวข้อที่เตรียมไว้ ไม่ใช่ AI ที่คุยได้ทุกเรื่อง",
        ],
        steps: [
          "อัดเสียงเซสชัน หรืออัปโหลดไฟล์เสียง",
          "ถอดเสียงเป็นข้อความให้คุณตรวจและแก้",
          "กำหนดว่าแต่ละบรรทัดเป็นเสียงเด็กหรือนักบำบัด",
          "คำนวณค่าทางภาษา เช่น ความยาวถ้อยความเฉลี่ย (MLU)",
          "ร่างรายงานที่แก้ไข ส่งออก และพิมพ์ได้",
        ],
      },
      howto: {
        lines: ["หนึ่งเซสชันมี 5 ขั้น:", "ทุกขั้นมีปุ่มให้กดในบทสนทนา เริ่มจากปุ่มด้านล่างได้เลย"],
        steps: [
          "เลือกเคส หรือสร้างเคสใหม่",
          "ยืนยันความยินยอมของผู้ปกครอง",
          "อัดเสียง หรืออัปโหลดไฟล์เสียง",
          "ตรวจบทถอดเสียง และกำหนดผู้พูดของแต่ละบรรทัด",
          "ดูค่าทางภาษา แล้วร่างรายงาน",
        ],
      },
      transcript: {
        lines: [
          "หลังส่งเสียง PasaScope จะถอดเสียงเป็นข้อความทีละบรรทัดพร้อมเวลา",
          "บทถอดเสียงเป็นร่างจากเครื่องและผิดได้ โดยเฉพาะเสียงของเด็ก ควรตรวจทุกบรรทัดก่อนนำไปใช้",
          "ในหน้าบทถอดเสียงของเซสชัน คุณแก้ข้อความ แยกบรรทัด และฟังเสียงทีละบรรทัดได้",
        ],
      },
      speakers: {
        lines: ["คุณเป็นผู้กำหนดว่าใครพูดแต่ละบรรทัด ในหน้าบทถอดเสียงของเซสชัน บรรทัดที่ยังไม่มีผู้พูดจะแสดงเป็น UNK"],
        steps: [
          "กดปุ่ม เด็ก หรือ นักบำบัด ที่บรรทัดนั้น ระบบจะเลื่อนไปบรรทัดถัดไปที่ยังไม่มีผู้พูด",
          "ใช้แป้นพิมพ์ได้: ลูกศรเลือกบรรทัด 1 คือเด็ก 2 คือนักบำบัด Space เล่นเสียงของบรรทัดนั้น",
          "ถ้าบรรทัดเดียวมีสองคนพูด วางเคอร์เซอร์ตรงจุดที่ต้องการแยก แล้วกด Ctrl+Enter",
          "ตั้งทุกบรรทัดที่ยังไม่มีผู้พูดเป็นคนเดียวกันได้ในครั้งเดียว แล้วแก้เฉพาะบรรทัดที่ต่าง",
        ],
      },
      measures: {
        lines: [
          "PasaScope คำนวณจากถ้อยความของเด็กในบทถอดเสียง: ความยาวถ้อยความเฉลี่ย (MLU) จำนวนคำทั้งหมด และจำนวนคำที่ไม่ซ้ำกัน",
          "ค่าเหล่านี้เป็นข้อสังเกตเชิงพรรณนา ไม่ใช่การตัดสินหรือการวินิจฉัย",
          "ถ้าบทถอดเสียงเปลี่ยนหลังจากนั้น ต้องคำนวณค่าใหม่",
        ],
      },
      formats: {
        lines: [
          "ใช้ไฟล์เสียง WAV, MP3, M4A, MP4, WebM และ OGG ได้",
          "เมื่อการถอดเสียงใช้บริการภายนอก ไฟล์ต้องไม่เกิน 25 MB ไฟล์ที่ใหญ่กว่านั้นจะถูกหยุดก่อนอัปโหลด",
        ],
      },
      privacy: {
        lines: [
          "ข้อมูลของคุณอยู่ในพื้นที่ทำงานของคุณเอง ผู้ใช้คนอื่นเปิดดูไม่ได้",
          "เมื่อการถอดเสียงใช้บริการภายนอก ไฟล์เสียงจะถูกส่งไปที่บริการนั้น และ PasaScope จะบอกก่อนที่คุณจะส่ง",
          "ใช้รหัสหรือชื่อเรียกแทนชื่อ-นามสกุลจริงของเด็ก",
          "การถอนความยินยอมของเคสจะลบไฟล์เสียงของเคสนั้น",
        ],
      },
      consent: {
        lines: [
          "ต้องยืนยันความยินยอมของผู้ปกครองก่อนเก็บเสียง ถ้ายังไม่ยืนยันจะสร้างเซสชันไม่ได้",
          "ยืนยันครั้งเดียวต่อหนึ่งเคส",
          "ถอนความยินยอมได้ที่หน้าของเคส ซึ่งจะลบไฟล์เสียงของเคสนั้น",
        ],
      },
      delete: {
        lines: [
          "ช่องนี้ลบข้อมูลไม่ได้ เพื่อไม่ให้มีอะไรถูกลบเพราะพิมพ์ผิด",
          "ถ้าต้องการลบไฟล์เสียงของเคส ให้ถอนความยินยอมที่หน้าของเคสนั้น",
          "ถ้าต้องการลบทั้งบัญชีพร้อมข้อมูลทั้งหมด ไปที่ ตั้งค่า › ความปลอดภัยและข้อมูล",
        ],
      },
      diagnosis: {
        lines: [
          "PasaScope ไม่วินิจฉัย และไม่บอกว่าเด็กปกติหรือไม่ปกติ",
          "ระบบถอดเสียงตัวอย่างภาษาและสรุปค่าทางภาษาจากตัวอย่างนั้น การแปลผลเป็นหน้าที่ของนักแก้ไขการพูด",
          "ระบบยังไม่ผ่านการตรวจสอบความเที่ยงตรงทางคลินิกสำหรับภาษาไทย",
        ],
      },
      language: { lines: ["เลือกภาษาของหน้าจอ"] },
      settings: {
        lines: ["ออกจากระบบได้ที่ปุ่มข้างชื่อของคุณในแถบนำทาง ส่วนการตั้งค่าอื่นอยู่ที่หน้าตั้งค่า"],
      },
      identity: {
        lines: [
          "นี่คือตัวช่วยของ PasaScope ไม่ใช่ AI และไม่ใช่คน",
          "ระบบจับคำที่คุณพิมพ์แล้วตอบด้วยคำตอบที่เตรียมไว้ จึงช่วยได้เฉพาะเรื่องการใช้งาน PasaScope",
        ],
      },
      thanks: { lines: ["ยินดี มีอะไรถามได้อีกเสมอ"] },
      bye: { lines: ["แล้วพบกันใหม่ เซสชันของคุณยังอยู่ที่เดิม"] },
    },
    today: {
      some: (count) => `มี ${count} เซสชันที่ลงวันที่วันนี้`,
      none: "ไม่มีเซสชันที่ลงวันที่วันนี้",
      noSchedule: "PasaScope ไม่มีปฏิทินนัดหมาย จึงแสดงเซสชันล่าสุดที่ลงวันที่วันนี้",
      pendingToo: (count) => `ยังมีอีก ${count} เซสชันจากวันก่อนที่ทำไม่จบ`,
    },
    pending: {
      some: (count) => `มี ${count} เซสชันที่ยังทำไม่จบ`,
      none: "ไม่มีงานค้าง เซสชันล่าสุดทุกเซสชันมีร่างรายงานแล้ว",
      noSessions: "ยังไม่มีเซสชัน",
    },
    cases: {
      some: (count) => `คุณมี ${count} เคส`,
      none: "ยังไม่มีเคส",
      more: (count) => `อีก ${count} เคสอยู่ในหน้าเคส`,
    },
    reports: {
      about: "รายงานร่างจากค่าทางภาษาของเซสชัน คุณแก้ไข ส่งออก และพิมพ์ได้",
      ready: (count) => `มี ${count} เซสชันล่าสุดที่มีร่างรายงานแล้ว`,
      none: "ยังไม่มีเซสชันล่าสุดที่มีร่างรายงาน",
    },
    unknown: {
      lines: ["ยังไม่เข้าใจข้อความนี้", "ช่องนี้ตอบคำถามเรื่องการใช้งาน PasaScope ลองถามให้สั้นลง หรือเลือกจากคำถามด้านล่าง"],
    },
  },
});
