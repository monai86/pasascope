import { defineMessages } from "@/i18n/messages";

type RecorderStatus = "recording" | "paused" | "stopped" | "interrupted" | "idle";
type JobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled" | "unavailable";

type AudioCaptureCopy = {
  recorder: {
    status: Record<RecorderStatus, string>;
    amplitude: string;
    start: string;
    pause: string;
    resume: string;
    stop: string;
    playback: string;
    rerecord: string;
    deleteLabel: string;
    delete: string;
    clearedForPrivacy: string;
    experimental: string;
    experimentalExternal: string;
    memoryOnly: string;
    errors: { unsupported: string; interrupted: string; permissionDenied: string; notStarted: string; empty: string };
  };
  upload: {
    regionLabel: string;
    title: string;
    recording: (duration: string, sizeMb: string) => string;
    privacyLabel: string;
    privacyBody: string;
    notStored: string;
    backendUnavailable: string;
    uploading: string;
    upload: string;
    cancel: string;
  };
  job: {
    regionLabel: string;
    status: Record<JobStatus, string>;
    waiting: (elapsed: string) => string;
    fallback: (reason: string) => string;
    requestedUsed: (requested: string, used: string) => string;
    transcribedBy: (provider: string) => string;
    providers: Record<string, string>;
    draftLabel: string;
    draftNote: (reviewClause: string) => string;
    review: string;
    retry: string;
    usePaste: string;
  };
};

export const audioCaptureMessages = defineMessages<AudioCaptureCopy>({
  en: {
    recorder: {
      status: {
        recording: "Recording",
        paused: "Paused",
        stopped: "Recording ready",
        interrupted: "Interrupted",
        idle: "Ready to record",
      },
      amplitude: "Microphone amplitude",
      start: "Start recording",
      pause: "Pause recording",
      resume: "Resume recording",
      stop: "Stop recording",
      playback: "Recorded audio playback",
      rerecord: "Re-record",
      deleteLabel: "Delete recording",
      delete: "Delete",
      clearedForPrivacy: "Unsaved recording was cleared for privacy. Please record again.",
      experimental:
        "Transcription is experimental. After you upload, the recording is transcribed on this server and the draft must be reviewed.",
      experimentalExternal:
        "Transcription is experimental. After you upload, the recording is sent to an external transcription service. The draft has no speaker labels and must be reviewed.",
      memoryOnly: "Audio stays in memory only while this page is open. It is not uploaded automatically.",
      errors: {
        unsupported: "Audio recording is not supported in this browser.",
        interrupted: "Recording was interrupted. Please record again.",
        permissionDenied: "Microphone permission was denied.",
        notStarted: "Microphone could not be started. Check the device and try again.",
        empty: "The recording was empty. Please record again.",
      },
    },
    upload: {
      regionLabel: "Audio upload confirmation",
      title: "Ready to upload for transcription",
      recording: (duration, sizeMb) => `Recording: ${duration} · ${sizeMb} MB`,
      privacyLabel: "Privacy notice:",
      privacyBody:
        "Audio will be sent to the backend for transcription. The transcript must be reviewed by a therapist before any features are extracted.",
      notStored: "Audio bytes are not stored in your browser. They are uploaded once and processed server-side.",
      backendUnavailable: "Backend unavailable — upload disabled. Use manual paste or .cha import instead.",
      uploading: "Uploading…",
      upload: "Upload for transcription",
      cancel: "Cancel",
    },
    job: {
      regionLabel: "Transcription job status",
      status: {
        queued: "Queued",
        processing: "Processing",
        completed: "Draft transcript ready",
        failed: "Transcription failed",
        cancelled: "Cancelled",
        unavailable: "Provider unavailable",
      },
      waiting: (elapsed) => `Waiting ${elapsed}`,
      fallback: (reason) => `Fallback: ${reason}`,
      requestedUsed: (requested, used) => `Requested: ${requested} · Used: ${used}`,
      transcribedBy: (provider) => `Transcribed by: ${provider}`,
      providers: {
        local_whisper: "Whisper (on this server)",
        hosted_whisper: "Whisper (external service)",
        mock: "Synthetic demo text — not speech recognition",
        manual: "Manual entry",
      },
      draftLabel: "Draft ASR transcript.",
      draftNote: (reviewClause) => `${reviewClause} before feature extraction.`,
      review: "Review transcript",
      retry: "Retry",
      usePaste: "Use manual paste instead",
    },
  },
  th: {
    recorder: {
      status: {
        recording: "กำลังบันทึกเสียง",
        paused: "หยุดชั่วคราว",
        stopped: "บันทึกเสียงเสร็จแล้ว",
        interrupted: "การบันทึกถูกขัดจังหวะ",
        idle: "พร้อมบันทึกเสียง",
      },
      amplitude: "ระดับเสียงจากไมโครโฟน",
      start: "เริ่มบันทึกเสียง",
      pause: "หยุดบันทึกชั่วคราว",
      resume: "บันทึกเสียงต่อ",
      stop: "หยุดบันทึกเสียง",
      playback: "ฟังเสียงที่บันทึก",
      rerecord: "บันทึกใหม่",
      deleteLabel: "ลบเสียงที่บันทึก",
      delete: "ลบ",
      clearedForPrivacy: "เสียงที่ยังไม่ได้บันทึกเก็บถูกล้างออกเพื่อความเป็นส่วนตัว กรุณาบันทึกเสียงใหม่",
      experimental: "การถอดเสียงยังอยู่ในขั้นทดลอง เมื่ออัปโหลดแล้ว เสียงจะถูกถอดบนเซิร์ฟเวอร์นี้ และต้องทบทวนร่างที่ได้",
      experimentalExternal:
        "การถอดเสียงยังอยู่ในขั้นทดลอง เมื่ออัปโหลดแล้ว เสียงจะถูกส่งไปยังบริการถอดเสียงภายนอก ร่างที่ได้ยังไม่ระบุผู้พูด และต้องทบทวนก่อนใช้",
      memoryOnly: "เสียงอยู่ในหน่วยความจำเฉพาะขณะเปิดหน้านี้ และไม่ถูกอัปโหลดเองโดยอัตโนมัติ",
      errors: {
        unsupported: "เบราว์เซอร์นี้ไม่รองรับการบันทึกเสียง",
        interrupted: "การบันทึกเสียงถูกขัดจังหวะ กรุณาบันทึกใหม่",
        permissionDenied: "ไม่ได้รับอนุญาตให้ใช้ไมโครโฟน",
        notStarted: "เริ่มใช้ไมโครโฟนไม่ได้ ตรวจอุปกรณ์แล้วลองอีกครั้ง",
        empty: "เสียงที่บันทึกว่างเปล่า กรุณาบันทึกใหม่",
      },
    },
    upload: {
      regionLabel: "ยืนยันการอัปโหลดเสียง",
      title: "พร้อมอัปโหลดเพื่อถอดเสียง",
      recording: (duration, sizeMb) => `เสียงที่บันทึก: ${duration} · ${sizeMb} MB`,
      privacyLabel: "ประกาศความเป็นส่วนตัว:",
      privacyBody: "เสียงจะถูกส่งไปยังเซิร์ฟเวอร์เพื่อถอดเสียง นักบำบัดต้องทบทวนบทถอดเสียงก่อนสกัดค่าทางภาษาใดๆ",
      notStored: "ข้อมูลเสียงไม่ถูกเก็บในเบราว์เซอร์ของคุณ เสียงจะถูกอัปโหลดครั้งเดียวและประมวลผลบนเซิร์ฟเวอร์",
      backendUnavailable: "ติดต่อเซิร์ฟเวอร์ไม่ได้ จึงปิดการอัปโหลด ใช้การวางบทถอดเสียงหรือนำเข้าไฟล์ .cha แทน",
      uploading: "กำลังอัปโหลด…",
      upload: "อัปโหลดเพื่อถอดเสียง",
      cancel: "ยกเลิก",
    },
    job: {
      regionLabel: "สถานะงานถอดเสียง",
      status: {
        queued: "รอคิว",
        processing: "กำลังประมวลผล",
        completed: "ร่างบทถอดเสียงพร้อมแล้ว",
        failed: "ถอดเสียงไม่สำเร็จ",
        cancelled: "ยกเลิกแล้ว",
        unavailable: "ตัวถอดเสียงใช้งานไม่ได้",
      },
      waiting: (elapsed) => `รอมาแล้ว ${elapsed}`,
      fallback: (reason) => `ใช้ทางสำรอง: ${reason}`,
      requestedUsed: (requested, used) => `ที่ขอ: ${requested} · ที่ใช้จริง: ${used}`,
      transcribedBy: (provider) => `ถอดเสียงโดย: ${provider}`,
      providers: {
        local_whisper: "Whisper (บนเซิร์ฟเวอร์นี้)",
        hosted_whisper: "Whisper (บริการภายนอก)",
        mock: "ข้อความสังเคราะห์สำหรับสาธิต ไม่ใช่การรู้จำเสียงพูด",
        manual: "ป้อนเอง",
      },
      draftLabel: "ร่างบทถอดเสียงจากการถอดเสียงอัตโนมัติ",
      draftNote: (reviewClause) => `${reviewClause}ก่อนสกัดค่าทางภาษา`,
      review: "ทบทวนบทถอดเสียง",
      retry: "ลองอีกครั้ง",
      usePaste: "วางบทถอดเสียงเองแทน",
    },
  },
});
