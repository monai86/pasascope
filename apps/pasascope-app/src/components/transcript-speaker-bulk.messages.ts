import { defineMessages } from "@/i18n/messages";

/** Speaker assignment in the transcript editor: the bar for every unknown line, and the controls on each line. */
type SpeakerBulkCopy = {
  unassigned: (count: number) => string;
  setAllTo: string;
  child: string;
  therapist: string;
  hint: string;
  childShort: string;
  therapistShort: string;
  setSpeaker: (lineNumber: number, speaker: string) => string;
  playLine: (lineNumber: number) => string;
  splitHint: string;
  shortcuts: string;
};

export const speakerBulkMessages = defineMessages<SpeakerBulkCopy>({
  en: {
    unassigned: (count) => `${count} ${count === 1 ? "line has" : "lines have"} no speaker.`,
    setAllTo: "Set them all to",
    child: "Child (CHI)",
    therapist: "Therapist (THER)",
    hint: "Then change the lines spoken by the other person one by one.",
    childShort: "Child",
    therapistShort: "Therapist",
    setSpeaker: (lineNumber, speaker) => `Set line ${lineNumber} to ${speaker}`,
    playLine: (lineNumber) => `Play line ${lineNumber}`,
    splitHint: "When two people are in one line, put the cursor where the second person starts, then choose Split line in the ⋯ menu.",
    shortcuts: "Shortcuts: ↑ ↓ choose a line · 1 child · 2 therapist · Space play the line · Ctrl+Enter in the text splits the line at the cursor",
  },
  th: {
    unassigned: (count) => `มี ${count} บรรทัดที่ยังไม่ระบุผู้พูด`,
    setAllTo: "ตั้งทั้งหมดเป็น",
    child: "เด็ก (CHI)",
    therapist: "นักบำบัด (THER)",
    hint: "จากนั้นแก้บรรทัดที่อีกคนพูดทีละบรรทัด",
    childShort: "เด็ก",
    therapistShort: "นักบำบัด",
    setSpeaker: (lineNumber, speaker) => `ตั้งบรรทัด ${lineNumber} เป็น${speaker}`,
    playLine: (lineNumber) => `ฟังบรรทัด ${lineNumber}`,
    splitHint: "ถ้าบรรทัดเดียวมีสองคนพูด ให้วางเคอร์เซอร์ตรงที่คนที่สองเริ่มพูด แล้วเลือก Split line ในเมนู ⋯",
    shortcuts: "คีย์ลัด: ↑ ↓ เลือกบรรทัด · 1 เด็ก · 2 นักบำบัด · Space ฟังบรรทัด · Ctrl+Enter ในช่องข้อความเพื่อตัดบรรทัดตรงเคอร์เซอร์",
  },
});
