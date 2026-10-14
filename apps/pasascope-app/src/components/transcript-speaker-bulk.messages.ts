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
  /** The editor around the lines. */
  editor: {
    title: string;
    lineCount: (count: number) => string;
    addLine: string;
    attested: string;
    views: { label: string; table: string; chat: string };
    columns: { time: string; speaker: string; utterance: string };
    inspector: { show: string; hide: string; label: string; audio: string; qa: string; audioTitle: string; noAudio: string };
    /** The one mark a line carries when it needs a look, by the editor's own label for it. */
    marks: Record<string, string>;
    filters: Record<string, string>;
    filterLabel: string;
    shown: (count: number) => string;
    saveDraft: string;
    runQa: string;
  };
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
    editor: {
      title: "Transcript",
      lineCount: (count) => `${count} ${count === 1 ? "line" : "lines"}`,
      addLine: "Add line",
      attested: "Attested",
      views: { label: "Transcript view", table: "Lines", chat: "CHAT text" },
      columns: { time: "Time", speaker: "Speaker", utterance: "What was said" },
      inspector: { show: "Show audio and QA", hide: "Hide audio and QA", label: "Inspector view", audio: "Audio", qa: "QA", audioTitle: "Session audio", noAudio: "No recording is linked to this session." },
      marks: { Unclear: "Unclear", Review: "Check", Low: "Low confidence" },
      filters: { all: "All lines", needs_review: "Needs a look", low_confidence: "Low confidence", missing_speaker: "No speaker", possible_error: "Possible error", notes: "Notes" },
      filterLabel: "Show lines",
      shown: (count) => `${count} shown`,
      saveDraft: "Save draft",
      runQa: "Run QA",
    },
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
    editor: {
      title: "บทถอดเสียง",
      lineCount: (count) => `${count} บรรทัด`,
      addLine: "เพิ่มบรรทัด",
      attested: "รับรองแล้ว",
      views: { label: "มุมมองบทถอดเสียง", table: "รายบรรทัด", chat: "ข้อความ CHAT" },
      columns: { time: "เวลา", speaker: "ผู้พูด", utterance: "สิ่งที่พูด" },
      inspector: { show: "แสดงเสียงและ QA", hide: "ซ่อนเสียงและ QA", label: "มุมมองแผงข้าง", audio: "เสียง", qa: "QA", audioTitle: "เสียงของเซสชัน", noAudio: "เซสชันนี้ยังไม่มีไฟล์เสียง" },
      marks: { Unclear: "ฟังไม่ชัด", Review: "ควรตรวจ", Low: "ความมั่นใจต่ำ" },
      filters: { all: "ทุกบรรทัด", needs_review: "ควรตรวจ", low_confidence: "ความมั่นใจต่ำ", missing_speaker: "ยังไม่ระบุผู้พูด", possible_error: "อาจผิด", notes: "โน้ต" },
      filterLabel: "แสดงบรรทัด",
      shown: (count) => `แสดง ${count} บรรทัด`,
      saveDraft: "บันทึกร่าง",
      runQa: "ตรวจคุณภาพ",
    },
  },
});
