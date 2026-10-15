import { defineMessages } from "@/i18n/messages";

/** Listening along to the recording and assigning who spoke each line. */
type AudioReviewCopy = {
  player: {
    play: string;
    pause: string;
    seek: string;
    speed: string;
    loop: string;
    loopHint: string;
  };
  waveform: {
    recording: string;
    label: string;
    speakers: { child: string; clinician: string; other: string };
    overview: string;
    detail: string;
    hint: string;
    noWaveform: string;
  };
  stats: {
    label: string;
    childTalk: string;
    turns: string;
    latency: string;
  };
  shortcuts: {
    label: string;
    play: string;
    child: string;
    clinician: string;
    loop: string;
    replay: string;
  };
  lines: {
    title: string;
    count: (count: number) => string;
    onlyUnassigned: (count: number) => string;
    empty: string;
    noneUnassigned: string;
    playLine: (lineNumber: number) => string;
    pauseLine: (lineNumber: number) => string;
    speaker: (lineNumber: number) => string;
    text: (lineNumber: number) => string;
    placeholder: string;
    verified: string;
    echolalia: string;
    pronounReversal: string;
  };
  save: {
    status: Record<"idle" | "unsaved" | "saving" | "saved" | "failed", string>;
    save: string;
    saving: string;
    saved: string;
  };
  stale: string;
};

export const audioReviewMessages = defineMessages<AudioReviewCopy>({
  en: {
    player: {
      play: "Play",
      pause: "Pause",
      seek: "Position in the recording",
      speed: "Playback speed",
      loop: "Loop",
      loopHint: "Repeat the selected line",
    },
    waveform: {
      recording: "Session recording",
      label: "Recording waveform",
      speakers: { child: "Child", clinician: "Therapist", other: "Other or not set" },
      overview: "Whole recording. Click or tap to jump there.",
      detail: "Close-up of the lines around the playhead. Click or tap to jump; drag a line's edge to change its timing.",
      hint: "Click or tap the waveform to jump there · drag a line's edge to change its timing",
      noWaveform: "No waveform is available for this recording. You can still play it and assign speakers.",
    },
    stats: {
      label: "From the lines so far",
      childTalk: "Child talk time",
      turns: "Turns",
      latency: "Average wait before the child answers",
    },
    shortcuts: {
      label: "Keyboard",
      play: "play or pause",
      child: "child",
      clinician: "therapist",
      loop: "loop",
      replay: "replay line",
    },
    lines: {
      title: "Lines",
      count: (count) => `${count} ${count === 1 ? "line" : "lines"}`,
      onlyUnassigned: (count) => `Only lines with no speaker (${count})`,
      empty: "No lines were transcribed for this recording.",
      noneUnassigned: "Every line has a speaker.",
      playLine: (lineNumber) => `Play line ${lineNumber}`,
      pauseLine: (lineNumber) => `Pause line ${lineNumber}`,
      speaker: (lineNumber) => `Speaker for line ${lineNumber}`,
      text: (lineNumber) => `What was said in line ${lineNumber}`,
      placeholder: "Type what you hear",
      verified: "Checked by you",
      echolalia: "Echolalia",
      pronounReversal: "Pronoun reversal",
    },
    save: {
      status: {
        idle: "Not saved yet",
        unsaved: "Changes not saved",
        saving: "Saving…",
        saved: "All changes saved",
        failed: "Could not save. Try again.",
      },
      save: "Save transcript",
      saving: "Saving…",
      saved: "Saved",
    },
    stale: "You changed the transcript after it was analysed. Save it and analyse it again so the findings match.",
  },
  th: {
    player: {
      play: "เล่น",
      pause: "หยุดชั่วคราว",
      seek: "ตำแหน่งในไฟล์เสียง",
      speed: "ความเร็วในการเล่น",
      loop: "เล่นซ้ำ",
      loopHint: "เล่นบรรทัดที่เลือกซ้ำ",
    },
    waveform: {
      recording: "ไฟล์เสียงของเซสชัน",
      label: "คลื่นเสียงของไฟล์",
      speakers: { child: "เด็ก", clinician: "นักบำบัด", other: "อื่นๆ หรือยังไม่ระบุ" },
      overview: "ทั้งไฟล์ กดเพื่อไปยังช่วงนั้น",
      detail: "ภาพขยายรอบตำแหน่งที่เล่นอยู่ กดเพื่อไปยังช่วงนั้น ลากขอบของบรรทัดเพื่อปรับเวลา",
      hint: "กดที่คลื่นเสียงเพื่อไปยังช่วงนั้น · ลากขอบของบรรทัดเพื่อปรับเวลา",
      noWaveform: "ไฟล์นี้ไม่มีภาพคลื่นเสียง แต่ยังเล่นและระบุผู้พูดได้ตามปกติ",
    },
    stats: {
      label: "จากบรรทัดที่มีตอนนี้",
      childTalk: "เวลาพูดของเด็ก",
      turns: "การผลัดกันพูด",
      latency: "เวลารอก่อนเด็กตอบโดยเฉลี่ย",
    },
    shortcuts: {
      label: "แป้นพิมพ์",
      play: "เล่นหรือหยุด",
      child: "เด็ก",
      clinician: "นักบำบัด",
      loop: "เล่นซ้ำ",
      replay: "เล่นบรรทัดนี้อีกครั้ง",
    },
    lines: {
      title: "บรรทัด",
      count: (count) => `${count} บรรทัด`,
      onlyUnassigned: (count) => `เฉพาะที่ยังไม่ระบุผู้พูด (${count})`,
      empty: "ไม่มีบรรทัดที่ถอดได้จากไฟล์เสียงนี้",
      noneUnassigned: "ทุกบรรทัดระบุผู้พูดแล้ว",
      playLine: (lineNumber) => `เล่นบรรทัดที่ ${lineNumber}`,
      pauseLine: (lineNumber) => `หยุดบรรทัดที่ ${lineNumber}`,
      speaker: (lineNumber) => `ผู้พูดของบรรทัดที่ ${lineNumber}`,
      text: (lineNumber) => `ข้อความของบรรทัดที่ ${lineNumber}`,
      placeholder: "พิมพ์สิ่งที่ได้ยิน",
      verified: "คุณตรวจแล้ว",
      echolalia: "พูดเลียนคำ",
      pronounReversal: "ใช้สรรพนามสลับ",
    },
    save: {
      status: {
        idle: "ยังไม่ได้บันทึก",
        unsaved: "มีการแก้ไขที่ยังไม่บันทึก",
        saving: "กำลังบันทึก…",
        saved: "บันทึกการแก้ไขทั้งหมดแล้ว",
        failed: "บันทึกไม่สำเร็จ ลองอีกครั้ง",
      },
      save: "บันทึกบทถอดเสียง",
      saving: "กำลังบันทึก…",
      saved: "บันทึกแล้ว",
    },
    stale: "คุณแก้บทถอดเสียงหลังจากวิเคราะห์ไปแล้ว ให้บันทึกแล้ววิเคราะห์ใหม่ เพื่อให้ผลตรงกับบทถอดเสียง",
  },
});
