import { defineMessages } from "@/i18n/messages";

/**
 * The line-by-line transcript editor. The English names of controls are also
 * their accessible names, which the tests and assistive technology rely on.
 */
type SpeakerBulkCopy = {
  unassigned: (count: number) => string;
  setAllTo: string;
  child: string;
  therapist: string;
  hint: string;
  playLine: (lineNumber: number) => string;
  shortcuts: string;
  editor: {
    title: string;
    lineCount: (count: number) => string;
    addLine: string;
    attested: string;
    views: { label: string; table: string; chat: string };
    /** The one mark a line carries when it needs a look, by the editor's own label for it. */
    marks: Record<string, string>;
    filters: Record<string, string>;
    filterLabel: string;
    shown: (count: number) => string;
    saveDraft: string;
    runQa: string;
    list: string;
    line: (lineNumber: number) => string;
    lineNumber: (lineNumber: number) => string;
    timestamp: (lineNumber: number) => string;
    speaker: (lineNumber: number) => string;
    utterance: (lineNumber: number) => string;
    placeholder: string;
    more: (lineNumber: number) => string;
    menu: (lineNumber: number) => string;
    split: string;
    mergePrevious: string;
    mergeNext: string;
    markUnclear: string;
    markClear: string;
    deleteLine: string;
    empty: string;
    noMatch: string;
    save: {
      label: string;
      status: Record<"idle" | "unsaved" | "saving" | "saved" | "failed", string>;
    };
    qaBlocked: Record<string, string>;
    qa: {
      title: string;
      status: Record<"not_run" | "pass" | "warning" | "fail", string>;
      items: (count: number) => string;
      none: string;
      notRun: string;
    };
    done: {
      title: string;
      body: string;
      addNote: string;
      attest: string;
      attested: string;
      export: string;
    };
  };
};

export const speakerBulkMessages = defineMessages<SpeakerBulkCopy>({
  en: {
    unassigned: (count) => `${count} ${count === 1 ? "line has" : "lines have"} no speaker.`,
    setAllTo: "Set them all to",
    child: "Child (CHI)",
    therapist: "Therapist (THER)",
    hint: "Then change the lines spoken by the other person one by one.",
    playLine: (lineNumber) => `Play line ${lineNumber}`,
    shortcuts: "↑ ↓ choose a line · 1 child · 2 therapist · Space play it · Ctrl+Enter in the text splits the line at the cursor",
    editor: {
      title: "Transcript",
      lineCount: (count) => `${count} ${count === 1 ? "line" : "lines"}`,
      addLine: "Add line",
      attested: "Attested",
      views: { label: "Transcript view", table: "Lines", chat: "CHAT text" },
      marks: { Unclear: "Unclear", Review: "Check", Low: "Low confidence" },
      filters: { all: "All lines", needs_review: "Needs a look", low_confidence: "Low confidence", missing_speaker: "No speaker", possible_error: "Possible error", notes: "Notes" },
      filterLabel: "Show lines",
      shown: (count) => `${count} shown`,
      saveDraft: "Save draft",
      runQa: "Run QA",
      list: "Transcript lines",
      line: (lineNumber) => `Transcript line ${lineNumber}`,
      lineNumber: (lineNumber) => `Line ${lineNumber}`,
      timestamp: (lineNumber) => `Timestamp for line ${lineNumber}`,
      speaker: (lineNumber) => `Speaker for line ${lineNumber}`,
      utterance: (lineNumber) => `Utterance text ${lineNumber}`,
      placeholder: "Type what was said",
      more: (lineNumber) => `More actions for line ${lineNumber}`,
      menu: (lineNumber) => `Actions for transcript line ${lineNumber}`,
      split: "Split line",
      mergePrevious: "Merge with previous",
      mergeNext: "Merge with next",
      markUnclear: "Mark unclear",
      markClear: "Mark clear",
      deleteLine: "Delete line",
      empty: "Add a transcript line to begin review.",
      noMatch: "No lines match the current review filter.",
      save: {
        label: "Transcript save status",
        status: {
          idle: "Transcript not saved",
          unsaved: "Unsaved transcript changes",
          saving: "Saving transcript",
          saved: "Transcript saved",
          failed: "Failed to save transcript",
        },
      },
      qaBlocked: {
        "Add at least one transcript line before running QA.": "Add at least one transcript line before running QA.",
        "Wait for the transcript draft to finish saving before running QA.": "Wait for the transcript draft to finish saving before running QA.",
        "Save the transcript draft again before running QA.": "Save the transcript draft again before running QA.",
        "Save transcript edits before running QA.": "Save transcript edits before running QA.",
        "Save the transcript draft before running QA.": "Save the transcript draft before running QA.",
      },
      qa: {
        title: "Transcript QA",
        status: { not_run: "Not checked", pass: "Pass", warning: "Warning", fail: "Needs changes" },
        items: (count) => `${count} ${count === 1 ? "item" : "items"}`,
        none: "No QA issues were found.",
        notRun: "Run QA after saving your edits.",
      },
      done: {
        title: "When the transcript is right",
        body: "Add a note for anything the recording does not show, and export the reviewed transcript as a CHAT file.",
        addNote: "Add Note",
        attest: "Attest transcript",
        attested: "Transcript attested",
        export: "Export reviewed .cha",
      },
    },
  },
  th: {
    unassigned: (count) => `มี ${count} บรรทัดที่ยังไม่ระบุผู้พูด`,
    setAllTo: "ตั้งทั้งหมดเป็น",
    child: "เด็ก (CHI)",
    therapist: "นักบำบัด (THER)",
    hint: "จากนั้นแก้บรรทัดที่อีกคนพูดทีละบรรทัด",
    playLine: (lineNumber) => `ฟังบรรทัด ${lineNumber}`,
    shortcuts: "↑ ↓ เลือกบรรทัด · 1 เด็ก · 2 นักบำบัด · Space ฟังบรรทัด · Ctrl+Enter ในช่องข้อความเพื่อแยกบรรทัดตรงเคอร์เซอร์",
    editor: {
      title: "บทถอดเสียง",
      lineCount: (count) => `${count} บรรทัด`,
      addLine: "เพิ่มบรรทัด",
      attested: "รับรองแล้ว",
      views: { label: "มุมมองบทถอดเสียง", table: "รายบรรทัด", chat: "ข้อความ CHAT" },
      marks: { Unclear: "ฟังไม่ชัด", Review: "ควรตรวจ", Low: "ความมั่นใจต่ำ" },
      filters: { all: "ทุกบรรทัด", needs_review: "ควรตรวจ", low_confidence: "ความมั่นใจต่ำ", missing_speaker: "ยังไม่ระบุผู้พูด", possible_error: "อาจผิด", notes: "โน้ต" },
      filterLabel: "แสดงบรรทัด",
      shown: (count) => `แสดง ${count} บรรทัด`,
      saveDraft: "บันทึกร่าง",
      runQa: "ตรวจคุณภาพ",
      list: "บรรทัดของบทถอดเสียง",
      line: (lineNumber) => `บรรทัดที่ ${lineNumber}`,
      lineNumber: (lineNumber) => `บรรทัดที่ ${lineNumber}`,
      timestamp: (lineNumber) => `เวลาของบรรทัดที่ ${lineNumber}`,
      speaker: (lineNumber) => `ผู้พูดของบรรทัดที่ ${lineNumber}`,
      utterance: (lineNumber) => `ข้อความของบรรทัดที่ ${lineNumber}`,
      placeholder: "พิมพ์สิ่งที่พูด",
      more: (lineNumber) => `คำสั่งเพิ่มเติมของบรรทัดที่ ${lineNumber}`,
      menu: (lineNumber) => `คำสั่งของบรรทัดที่ ${lineNumber}`,
      split: "แยกบรรทัดตรงเคอร์เซอร์",
      mergePrevious: "รวมกับบรรทัดก่อนหน้า",
      mergeNext: "รวมกับบรรทัดถัดไป",
      markUnclear: "ทำเครื่องหมายว่าฟังไม่ชัด",
      markClear: "เอาเครื่องหมายฟังไม่ชัดออก",
      deleteLine: "ลบบรรทัด",
      empty: "เพิ่มบรรทัดเพื่อเริ่มตรวจบทถอดเสียง",
      noMatch: "ไม่มีบรรทัดที่ตรงกับตัวกรองนี้",
      save: {
        label: "สถานะการบันทึกบทถอดเสียง",
        status: {
          idle: "ยังไม่ได้บันทึก",
          unsaved: "มีการแก้ไขที่ยังไม่บันทึก",
          saving: "กำลังบันทึก…",
          saved: "บันทึกแล้ว",
          failed: "บันทึกไม่สำเร็จ ลองอีกครั้ง",
        },
      },
      qaBlocked: {
        "Add at least one transcript line before running QA.": "เพิ่มอย่างน้อยหนึ่งบรรทัดก่อนตรวจคุณภาพ",
        "Wait for the transcript draft to finish saving before running QA.": "รอให้บันทึกเสร็จก่อนตรวจคุณภาพ",
        "Save the transcript draft again before running QA.": "บันทึกอีกครั้งก่อนตรวจคุณภาพ",
        "Save transcript edits before running QA.": "บันทึกการแก้ไขก่อนตรวจคุณภาพ",
        "Save the transcript draft before running QA.": "บันทึกร่างก่อนตรวจคุณภาพ",
      },
      qa: {
        title: "ผลตรวจคุณภาพ",
        status: { not_run: "ยังไม่ได้ตรวจ", pass: "ผ่าน", warning: "มีข้อควรระวัง", fail: "ต้องแก้ไข" },
        items: (count) => `${count} รายการ`,
        none: "ไม่พบปัญหา",
        notRun: "บันทึกการแก้ไขแล้วกดตรวจคุณภาพ",
      },
      done: {
        title: "เมื่อบทถอดเสียงถูกต้องแล้ว",
        body: "เพิ่มโน้ตสำหรับสิ่งที่ไฟล์เสียงไม่ได้บอก และส่งออกบทถอดเสียงที่ตรวจแล้วเป็นไฟล์ CHAT ได้",
        addNote: "เพิ่มโน้ต",
        attest: "รับรองบทถอดเสียง",
        attested: "รับรองบทถอดเสียงแล้ว",
        export: "ส่งออกไฟล์ .cha",
      },
    },
  },
});
