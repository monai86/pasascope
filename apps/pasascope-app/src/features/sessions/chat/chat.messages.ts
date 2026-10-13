import type { BlockedReason, ChatStep, ReplyAction } from "@/features/sessions/chat/chat-thread-model";
import { defineMessages } from "@/i18n/messages";

/**
 * Everything the session conversation says. The app speaks plainly and only
 * about what it did or what the session needs next; it never interprets a
 * measure or suggests a conclusion about the child.
 */
type ChatCopy = {
  threadLabel: string;
  stepsLabel: string;
  steps: Record<ChatStep, string>;
  stepOf: (current: number, total: number) => string;
  stepDone: string;
  loading: string;
  loadFailed: string;
  reload: string;
  consentInactive: string;
  openCase: string;
  askAudio: {
    recording: string;
    audio: string;
    chooseFile: string;
    formats: string;
    unsupported: string;
    useFileInstead: string;
    recordInstead: string;
    transcriptHint: string;
  };
  audioChip: { title: string; minutes: (clock: string) => string };
  transcriptFile: string;
  confirmUpload: { ask: string; tooLarge: string };
  transcribing: { uploading: string; working: string; elapsed: (clock: string) => string };
  transcriptionFailed: { failed: string; unavailable: string };
  transcript: {
    ready: (lines: number) => string;
    readyFromFile: (lines: number) => string;
    unknownSome: (count: number) => string;
    unknownAll: string;
    empty: string;
    speakers: { child: string; therapist: string; unknown: string };
    viewAll: string;
  };
  saveFailed: string;
  speakersComplete: { assigned: string; ready: string };
  measuring: string;
  measuresFailed: string;
  measuresStale: string;
  measures: {
    intro: (childUtterances: number | null) => string;
    mlu: string;
    mluUnit: string;
    previous: (value: string) => string;
    totalWords: string;
    distinctWords: string;
    noValue: string;
    descriptive: string;
  };
  reporting: string;
  reportFailed: string;
  reportStale: string;
  reportReady: { draft: string; signed: string };
  said: {
    assignedTherapist: (count: number) => string;
    assignedChild: (count: number) => string;
    extract: string;
    report: string;
    note: string;
  };
  replies: Record<ReplyAction, string>;
  blocked: Record<BlockedReason, string>;
  composer: {
    label: string;
    placeholder: string;
    submit: string;
    attach: string;
    saved: string;
    failed: string;
    attachFailed: string;
  };
  panel: {
    trigger: string;
    ageYearsMonths: (years: number, months: number) => string;
    audio: string;
    play: string;
    pause: string;
    of: (clock: string) => string;
    date: string;
    language: string;
    consent: string;
    consentGranted: string;
    consentNotGranted: string;
    notes: string;
    noNotes: string;
    newSession: string;
  };
};

export const chatMessages = defineMessages<ChatCopy>({
  en: {
    threadLabel: "Session conversation",
    stepsLabel: "Session steps",
    steps: {
      audio: "Send audio",
      transcript: "Check the transcript",
      measures: "See the language measures",
      report: "Report",
    },
    stepOf: (current, total) => `Step ${current} of ${total}`,
    stepDone: "done",
    loading: "Opening the session…",
    loadFailed: "This session could not be opened.",
    reload: "Try again",
    consentInactive:
      "Caregiver consent for this case is not active, so audio cannot be collected or processed for it.",
    openCase: "Open the case page",
    askAudio: {
      recording: "Start recording when you are ready. When you stop, I will ask before anything is sent for transcription.",
      audio: "Choose the audio file for this session.",
      chooseFile: "Choose an audio file",
      formats: "WAV, MP3, M4A, MP4, WebM or OGG",
      unsupported: "That file is not a supported audio format.",
      useFileInstead: "Upload a file instead",
      recordInstead: "Record here instead",
      transcriptHint: "Already have a .cha transcript? Attach it with the paperclip below.",
    },
    audioChip: { title: "Session audio", minutes: (clock) => `${clock} min` },
    transcriptFile: "Transcript file (.cha)",
    confirmUpload: {
      ask: "Send this audio for transcription?",
      tooLarge: "This file is larger than 25 MB, the limit of the transcription service.",
    },
    transcribing: {
      uploading: "Uploading the audio…",
      working: "Transcribing. This can take a while; you can leave this page open.",
      elapsed: (clock) => `${clock} so far`,
    },
    transcriptionFailed: {
      failed: "Transcription did not finish.",
      unavailable:
        "Speech recognition is not switched on for this server, so the audio was not uploaded. You can attach a .cha transcript instead.",
    },
    transcript: {
      ready: (lines) => `Transcription is done: ${lines} ${lines === 1 ? "line" : "lines"}.`,
      readyFromFile: (lines) => `The transcript is in: ${lines} ${lines === 1 ? "line" : "lines"}.`,
      unknownSome: (count) => `${count} ${count === 1 ? "line still has" : "lines still have"} no speaker.`,
      unknownAll: "No line has a speaker yet. Open the transcript to mark who says each line.",
      empty: "The transcript has no lines yet.",
      speakers: { child: "Child", therapist: "Therapist", unknown: "Speaker unknown" },
      viewAll: "See the whole transcript",
    },
    saveFailed: "The transcript could not be saved. The change is not saved yet.",
    speakersComplete: {
      assigned: "Done. Every line now has a speaker, and the language measures can be extracted.",
      ready: "Every line has a speaker. The language measures can be extracted.",
    },
    measuring: "Extracting the language measures from the transcript…",
    measuresFailed: "The language measures could not be extracted. No result was recorded.",
    measuresStale: "The transcript changed after the measures were taken, so those values no longer apply.",
    measures: {
      intro: (childUtterances) =>
        childUtterances === null
          ? "Here are this session's language measures."
          : `Here are this session's language measures, from ${childUtterances} child ${childUtterances === 1 ? "utterance" : "utterances"}.`,
      mlu: "Mean length of utterance (MLU)",
      mluUnit: "words per utterance",
      previous: (value) => `previous session ${value}`,
      totalWords: "Total words",
      distinctWords: "Different words",
      noValue: "No value",
      descriptive: "These values are descriptive observations.",
    },
    reporting: "Preparing the report draft…",
    reportFailed: "The report draft could not be created. No draft was made.",
    reportStale: "The transcript or the measures changed after the report was drafted, so a new draft is needed.",
    reportReady: {
      draft: "The report draft is ready. Every sentence can be edited and it needs your review before use.",
      signed: "This report has been signed.",
    },
    said: {
      assignedTherapist: (count) => `The other ${count} ${count === 1 ? "line is" : "lines are"} the therapist`,
      assignedChild: (count) => `The other ${count} ${count === 1 ? "line is" : "lines are"} the child`,
      extract: "Extract the language measures",
      report: "Draft the report",
      note: "Note",
    },
    replies: {
      "upload-audio": "Send for transcription",
      "discard-audio": "Don't use this audio",
      "retry-audio": "Try again",
      "assign-therapist": "The rest are the therapist",
      "assign-child": "The rest are the child",
      "open-transcript": "Open the transcript",
      "extract-measures": "Extract the language measures",
      "open-measures": "See all the measures",
      "generate-report": "Draft the report",
      "open-report": "Open the report draft",
      "retry-save": "Save again",
    },
    blocked: {
      "no-child-lines": "No line is marked as the child's yet. The measures are computed from the child's utterances.",
      "unsaved-transcript": "The transcript has to be saved first.",
    },
    composer: {
      label: "Session note",
      placeholder: "Write a note for this session…",
      submit: "Save note",
      attach: "Attach an audio file or a .cha transcript",
      saved: "Saved as a session note. Notes go into the report draft.",
      failed: "The note could not be saved.",
      attachFailed: "That file could not be read as a transcript.",
    },
    panel: {
      trigger: "Session details",
      ageYearsMonths: (years, months) => `${years} y ${months} m`,
      audio: "Session audio",
      play: "Play audio",
      pause: "Pause audio",
      of: (clock) => `of ${clock}`,
      date: "Date",
      language: "Language",
      consent: "Consent",
      consentGranted: "Given",
      consentNotGranted: "Not active",
      notes: "Notes",
      noNotes: "No notes yet",
      newSession: "Start a new session",
    },
  },
  th: {
    threadLabel: "บทสนทนาของเซสชัน",
    stepsLabel: "ขั้นตอนของเซสชัน",
    steps: {
      audio: "ส่งเสียง",
      transcript: "ตรวจบทถอดเสียง",
      measures: "ดูค่าทางภาษา",
      report: "รายงาน",
    },
    stepOf: (current, total) => `ขั้นที่ ${current} จาก ${total}`,
    stepDone: "เสร็จแล้ว",
    loading: "กำลังเปิดเซสชัน…",
    loadFailed: "เปิดเซสชันนี้ไม่สำเร็จ",
    reload: "ลองอีกครั้ง",
    consentInactive: "ความยินยอมของผู้ปกครองสำหรับเคสนี้ไม่ได้อยู่ในสถานะใช้งาน จึงยังเก็บหรือประมวลผลเสียงของเคสนี้ไม่ได้",
    openCase: "เปิดหน้าเคส",
    askAudio: {
      recording: "พร้อมแล้วกดเริ่มบันทึกได้เลย เมื่อหยุดบันทึก ระบบจะถามก่อนส่งเสียงไปถอดเสียง",
      audio: "เลือกไฟล์เสียงของเซสชันนี้",
      chooseFile: "เลือกไฟล์เสียง",
      formats: "รองรับ WAV, MP3, M4A, MP4, WebM และ OGG",
      unsupported: "ไฟล์นี้ไม่ใช่รูปแบบเสียงที่รองรับ",
      useFileInstead: "อัปโหลดไฟล์แทน",
      recordInstead: "อัดเสียงที่นี่แทน",
      transcriptHint: "มีบทถอดเสียง .cha อยู่แล้ว แนบได้จากปุ่มคลิปหนีบกระดาษด้านล่าง",
    },
    audioChip: { title: "เสียงของเซสชัน", minutes: (clock) => `${clock} นาที` },
    transcriptFile: "ไฟล์บทถอดเสียง (.cha)",
    confirmUpload: {
      ask: "ส่งเสียงนี้ไปถอดเสียงเลยไหม",
      tooLarge: "ไฟล์นี้ใหญ่กว่า 25 MB ซึ่งเกินขีดจำกัดของบริการถอดเสียง",
    },
    transcribing: {
      uploading: "กำลังอัปโหลดเสียง…",
      working: "กำลังถอดเสียง อาจใช้เวลาสักครู่ เปิดหน้านี้ค้างไว้ได้",
      elapsed: (clock) => `ผ่านไป ${clock}`,
    },
    transcriptionFailed: {
      failed: "ถอดเสียงไม่สำเร็จ",
      unavailable: "เซิร์ฟเวอร์นี้ยังไม่ได้เปิดระบบถอดเสียง จึงไม่ได้อัปโหลดเสียง แนบบทถอดเสียง .cha แทนได้",
    },
    transcript: {
      ready: (lines) => `ถอดเสียงเสร็จแล้ว ได้ ${lines} บรรทัด`,
      readyFromFile: (lines) => `อ่านบทถอดเสียงแล้ว ได้ ${lines} บรรทัด`,
      unknownSome: (count) => `เหลือ ${count} บรรทัดที่ยังไม่รู้ว่าใครพูด`,
      unknownAll: "ยังไม่มีบรรทัดไหนระบุผู้พูด เปิดบทถอดเสียงเพื่อระบุว่าใครพูดบรรทัดไหน",
      empty: "บทถอดเสียงยังไม่มีบรรทัด",
      speakers: { child: "เด็ก", therapist: "นักบำบัด", unknown: "ยังไม่รู้ผู้พูด" },
      viewAll: "ดูบทถอดเสียงทั้งหมด",
    },
    saveFailed: "บันทึกบทถอดเสียงไม่สำเร็จ การแก้ไขยังไม่ถูกบันทึก",
    speakersComplete: {
      assigned: "ตั้งผู้พูดให้แล้ว ตอนนี้ครบทุกบรรทัด พร้อมสกัดค่าทางภาษา",
      ready: "ระบุผู้พูดครบทุกบรรทัดแล้ว พร้อมสกัดค่าทางภาษา",
    },
    measuring: "กำลังสกัดค่าทางภาษาจากบทถอดเสียง…",
    measuresFailed: "สกัดค่าทางภาษาไม่สำเร็จ ยังไม่มีผลใดถูกบันทึก",
    measuresStale: "บทถอดเสียงถูกแก้หลังสกัดค่าครั้งก่อน ค่าเดิมจึงใช้ไม่ได้แล้ว",
    measures: {
      intro: (childUtterances) =>
        childUtterances === null
          ? "นี่คือค่าทางภาษาของเซสชันนี้"
          : `นี่คือค่าทางภาษาของเซสชันนี้ จากถ้อยความของเด็ก ${childUtterances} ถ้อยความ`,
      mlu: "ความยาวถ้อยความเฉลี่ย (MLU)",
      mluUnit: "คำต่อถ้อยความ",
      previous: (value) => `เซสชันก่อน ${value}`,
      totalWords: "คำทั้งหมด",
      distinctWords: "คำที่แตกต่างกัน",
      noValue: "ไม่มีค่า",
      descriptive: "ค่าเหล่านี้เป็นข้อสังเกตเชิงพรรณนา",
    },
    reporting: "กำลังเตรียมร่างรายงาน…",
    reportFailed: "สร้างร่างรายงานไม่สำเร็จ ยังไม่มีร่างถูกสร้าง",
    reportStale: "บทถอดเสียงหรือค่าทางภาษาเปลี่ยนไปหลังสร้างร่างรายงาน จึงต้องสร้างร่างใหม่",
    reportReady: {
      draft: "ร่างรายงานพร้อมแล้ว ทุกข้อความแก้ไขได้ และต้องทบทวนก่อนนำไปใช้",
      signed: "รายงานนี้ลงนามแล้ว",
    },
    said: {
      assignedTherapist: (count) => `อีก ${count} บรรทัดเป็นนักบำบัดพูด`,
      assignedChild: (count) => `อีก ${count} บรรทัดเป็นเด็กพูด`,
      extract: "สกัดค่าทางภาษา",
      report: "สร้างร่างรายงาน",
      note: "โน้ต",
    },
    replies: {
      "upload-audio": "ส่งไปถอดเสียง",
      "discard-audio": "ไม่ใช้เสียงนี้",
      "retry-audio": "ลองอีกครั้ง",
      "assign-therapist": "ที่เหลือเป็นนักบำบัดพูด",
      "assign-child": "ที่เหลือเป็นเด็กพูด",
      "open-transcript": "เปิดบทถอดเสียง",
      "extract-measures": "สกัดค่าทางภาษา",
      "open-measures": "ดูค่าทางภาษาทั้งหมด",
      "generate-report": "สร้างร่างรายงาน",
      "open-report": "เปิดร่างรายงาน",
      "retry-save": "บันทึกอีกครั้ง",
    },
    blocked: {
      "no-child-lines": "ยังไม่มีบรรทัดที่ระบุว่าเด็กเป็นผู้พูด ค่าทางภาษาคำนวณจากถ้อยความของเด็ก",
      "unsaved-transcript": "ต้องบันทึกบทถอดเสียงก่อน",
    },
    composer: {
      label: "โน้ตของเซสชัน",
      placeholder: "จดโน้ตของเซสชันนี้…",
      submit: "บันทึกโน้ต",
      attach: "แนบไฟล์เสียงหรือบทถอดเสียง (.cha)",
      saved: "บันทึกเป็นโน้ตของเซสชันแล้ว โน้ตจะอยู่ในร่างรายงาน",
      failed: "บันทึกโน้ตไม่สำเร็จ",
      attachFailed: "อ่านไฟล์นี้เป็นบทถอดเสียงไม่ได้",
    },
    panel: {
      trigger: "รายละเอียดเซสชัน",
      ageYearsMonths: (years, months) => `${years} ปี ${months} เดือน`,
      audio: "เสียงของเซสชัน",
      play: "เล่นเสียง",
      pause: "หยุดเสียง",
      of: (clock) => `จาก ${clock}`,
      date: "วันที่",
      language: "ภาษา",
      consent: "ความยินยอม",
      consentGranted: "ให้แล้ว",
      consentNotGranted: "ไม่ได้อยู่ในสถานะใช้งาน",
      notes: "โน้ต",
      noNotes: "ยังไม่มีโน้ต",
      newSession: "เริ่มเซสชันใหม่",
    },
  },
});
