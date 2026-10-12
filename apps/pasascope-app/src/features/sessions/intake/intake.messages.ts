import { defineMessages } from "@/i18n/messages";

type IntakeStep = "details" | "source" | "setup" | "review";
type IntakeSource = "recording" | "audio" | "cha" | "paste";

type IntakeCopy = {
  view: {
    title: string;
    description: string;
    meta: [string, string];
    finalNote: string;
    currentIntake: string;
    rowStep: string;
    rowSource: string;
    rowTranscriptStatus: string;
    readyForReview: string;
    pending: string;
    stepsLabel: string;
    stepOf: (step: number, total: number) => string;
    stepStates: { complete: string; current: string; available: string };
  };
  steps: Record<IntakeStep, string>;
  sources: Record<IntakeSource, string>;
  sourceChoices: Record<IntakeSource, string>;
  consent: { title: string; body: string; submit: string };
  details: {
    body: string;
    childClient: string;
    clinician: string;
    date: string;
    time: string;
    setting: string;
    settings: Record<string, string>;
    duration: string;
    minutes: (count: string) => string;
    goals: string;
    safetyNote: string;
    continue: string;
  };
  source: {
    body: string;
    recordingCaptured: string;
    uploadForTranscription: string;
    invalidExtension: string;
    invalidFile: string;
    previewTitle: string;
    previewOnly: string;
    noTranscriptTitle: string;
    noTranscriptBody: string;
    back: string;
    continue: string;
    audioBody: string;
    quickDemo: string;
    thaiSample: string;
    thaiSampleTitle: string;
    englishSample: string;
    englishSampleTitle: string;
    chaFileLabel: string;
    chaTextLabel: string;
    pasteTextLabel: string;
    importWarnings: string;
    chatValidation: string;
    saveTranscript: string;
  };
  setup: {
    body: string;
    speakerLabels: string;
    metadata: string;
    language: string;
    languages: Record<string, string>;
    sampleType: string;
    sampleTypes: Record<string, string>;
    requirements: string;
    reviewSpeakerLabels: string;
    reviewFeatureLock: string;
    back: string;
    continue: string;
  };
  review: {
    body: string;
    sessionSummary: string;
    workflowSummary: string;
    childClient: string;
    date: string;
    time: string;
    setting: string;
    duration: string;
    clinician: string;
    sourceType: string;
    transcriptSource: string;
    language: string;
    sampleType: string;
    goals: string;
    notSet: string;
    sourceReady: string;
    sourceNotReady: string;
    safetyNote: string;
    asrWarning: string;
    back: string;
    save: string;
    start: string;
  };
};

export const intakeMessages = defineMessages<IntakeCopy>({
  en: {
    view: {
      title: "Session Intake",
      description:
        "Capture session context, prepare source material, and route the workflow into therapist transcript review without weakening the existing review and attestation gates.",
      meta: ["Audio upload requires explicit confirmation", "ASR remains experimental"],
      finalNote: "Transcript must be reviewed before report use.",
      currentIntake: "Current intake",
      rowStep: "Step",
      rowSource: "Source",
      rowTranscriptStatus: "Transcript status",
      readyForReview: "Ready for review",
      pending: "Pending",
      stepsLabel: "Intake steps",
      stepOf: (step, total) => `Step ${step} of ${total}`,
      stepStates: { complete: "complete", current: "current step", available: "not started" },
    },
    steps: {
      details: "Session Details",
      source: "Source Material",
      setup: "Transcript Setup",
      review: "Review & Start",
    },
    sources: {
      recording: "Browser recording",
      audio: "Audio upload",
      cha: "CHAT file upload",
      paste: "Pasted transcript",
    },
    sourceChoices: {
      recording: "Record in browser",
      audio: "Upload audio",
      cha: "Upload .cha",
      paste: "Paste transcript",
    },
    consent: {
      title: "Consent Verification Required",
      body: "Audio processing, recording, and clinical observation suggested reviews are locked until parental/caregiver consent is verified.",
      submit: "Verify and Grant Consent",
    },
    details: {
      body: "Set the session context first so the transcript workflow carries the correct child label, timing, and therapist-entered goals.",
      childClient: "Child or client",
      clinician: "Clinician",
      date: "Session date",
      time: "Session time",
      setting: "Setting",
      settings: { clinic: "Clinic", home: "Home", telehealth: "Telehealth" },
      duration: "Duration",
      minutes: (count) => `${count} minutes`,
      goals: "Session goals",
      safetyNote:
        "Do not use this intake to imply diagnosis, automated conclusions, or secure sharing beyond the implemented local workflow.",
      continue: "Continue to Source Material",
    },
    source: {
      body: "Preserve the existing quick-start workflows while making the source choice explicit. Audio upload and ASR remain clearly labeled experimental.",
      recordingCaptured: "Recording captured. Ready for explicit upload confirmation.",
      uploadForTranscription: "Upload for transcription",
      invalidExtension: "Invalid .cha file: choose a file with the .cha extension.",
      invalidFile: "Invalid .cha file.",
      previewTitle: "Transcript preview",
      previewOnly: "Preview only",
      noTranscriptTitle: "No transcript available yet",
      noTranscriptBody: "Add source material, then continue into transcript setup and therapist review.",
      back: "Back to Session Details",
      continue: "Continue to Transcript Setup",
      audioBody:
        "Uploading an existing audio file is not available yet. Record in the browser to transcribe speech, or upload a .cha file or paste a transcript you already have.",
      quickDemo: "Quick Demo:",
      thaiSample: "ตัวอย่างภาษาไทย",
      thaiSampleTitle: "Load sample Thai conversation for demonstration",
      englishSample: "English Sample",
      englishSampleTitle: "Load sample English conversation",
      chaFileLabel: "CHA transcript file",
      chaTextLabel: "CHA transcript text",
      pasteTextLabel: "Pasted transcript text",
      importWarnings: "Import warnings",
      chatValidation: "CHAT validation",
      saveTranscript: "Save transcript",
    },
    setup: {
      body: "Define how the transcript should be reviewed. These fields do not unlock analysis on their own; QA and therapist attestation are still required later.",
      speakerLabels: "Speaker labels",
      metadata: "Session metadata",
      language: "Language",
      languages: { eng: "English", tha: "Thai", mixed: "Mixed language sample" },
      sampleType: "Sample type",
      sampleTypes: { conversation: "Conversation", play: "Play-based interaction", narrative: "Narrative sample" },
      requirements: "Review requirements",
      reviewSpeakerLabels: "I will review speaker labels and transcript wording before attestation.",
      reviewFeatureLock:
        "I understand feature extraction stays locked until transcript review, QA, and attestation are complete.",
      back: "Back to Source Material",
      continue: "Continue to Review & Start",
    },
    review: {
      body: "Confirm the summary, keep the privacy notice visible, and route into the existing transcript review workflow.",
      sessionSummary: "Session summary",
      workflowSummary: "Workflow summary",
      childClient: "Child/client",
      date: "Date",
      time: "Time",
      setting: "Setting",
      duration: "Duration",
      clinician: "Clinician",
      sourceType: "Source type",
      transcriptSource: "Transcript source",
      language: "Language",
      sampleType: "Sample type",
      goals: "Goals",
      notSet: "Not set",
      sourceReady: "Ready for therapist review",
      sourceNotReady: "Still needs transcript-ready input",
      safetyNote:
        "Audio bytes are not stored in browser persistent storage. Experimental ASR output must be reviewed by a therapist before transcript attestation, feature extraction, or report use.",
      asrWarning:
        "Audio upload and ASR remain experimental in this workflow. Start transcript review only after a draft transcript is actually available.",
      back: "Back to Transcript Setup",
      save: "Save session",
      start: "Start Transcript Review",
    },
  },
  th: {
    view: {
      title: "รับข้อมูลเซสชัน",
      description:
        "บันทึกบริบทของเซสชัน เตรียมแหล่งข้อมูล แล้วส่งต่อให้นักบำบัดทบทวนบทถอดเสียง โดยขั้นตอนทบทวนและรับรองยังอยู่ครบ",
      meta: ["การอัปโหลดเสียงต้องยืนยันก่อนทุกครั้ง", "การถอดเสียงอัตโนมัติยังอยู่ในขั้นทดลอง"],
      finalNote: "ต้องทบทวนบทถอดเสียงก่อนนำไปใช้ในรายงาน",
      currentIntake: "การรับข้อมูลตอนนี้",
      rowStep: "ขั้นตอน",
      rowSource: "แหล่งข้อมูล",
      rowTranscriptStatus: "สถานะบทถอดเสียง",
      readyForReview: "พร้อมให้ทบทวน",
      pending: "รอดำเนินการ",
      stepsLabel: "ขั้นตอนการรับข้อมูล",
      stepOf: (step, total) => `ขั้นที่ ${step} จาก ${total}`,
      stepStates: { complete: "เสร็จแล้ว", current: "ขั้นปัจจุบัน", available: "ยังไม่เริ่ม" },
    },
    steps: {
      details: "รายละเอียดเซสชัน",
      source: "แหล่งข้อมูล",
      setup: "ตั้งค่าบทถอดเสียง",
      review: "ตรวจทานและเริ่ม",
    },
    sources: {
      recording: "บันทึกเสียงในเบราว์เซอร์",
      audio: "อัปโหลดไฟล์เสียง",
      cha: "อัปโหลดไฟล์ CHAT",
      paste: "บทถอดเสียงที่วาง",
    },
    sourceChoices: {
      recording: "บันทึกเสียงในเบราว์เซอร์",
      audio: "อัปโหลดไฟล์เสียง",
      cha: "อัปโหลดไฟล์ .cha",
      paste: "วางบทถอดเสียง",
    },
    consent: {
      title: "ต้องยืนยันความยินยอมก่อน",
      body: "การประมวลผลเสียง การบันทึกเสียง และข้อสังเกตที่เสนอให้ทบทวนจะยังล็อกอยู่ จนกว่าจะยืนยันความยินยอมของผู้ปกครองหรือผู้ดูแล",
      submit: "ยืนยันและบันทึกความยินยอม",
    },
    details: {
      body: "กำหนดบริบทของเซสชันก่อน เพื่อให้ขั้นตอนบทถอดเสียงใช้ชื่อเรียกเด็ก เวลา และเป้าหมายที่นักบำบัดกรอกอย่างถูกต้อง",
      childClient: "เด็กหรือผู้รับบริการ",
      clinician: "นักบำบัด",
      date: "วันที่ของเซสชัน",
      time: "เวลาของเซสชัน",
      setting: "สถานที่",
      settings: { clinic: "คลินิก", home: "บ้าน", telehealth: "ออนไลน์" },
      duration: "ระยะเวลา",
      minutes: (count) => `${count} นาที`,
      goals: "เป้าหมายของเซสชัน",
      safetyNote:
        "อย่าใช้การรับข้อมูลนี้เพื่อสื่อถึงการวินิจฉัย ข้อสรุปอัตโนมัติ หรือการแชร์ที่ปลอดภัยเกินกว่าขั้นตอนในเครื่องที่ทำไว้จริง",
      continue: "ไปต่อที่แหล่งข้อมูล",
    },
    source: {
      body: "เลือกแหล่งข้อมูลของเซสชันนี้ การอัปโหลดเสียงและการถอดเสียงอัตโนมัติยังอยู่ในขั้นทดลอง",
      recordingCaptured: "บันทึกเสียงแล้ว พร้อมให้ยืนยันก่อนอัปโหลด",
      uploadForTranscription: "อัปโหลดเพื่อถอดเสียง",
      invalidExtension: "ไฟล์ .cha ไม่ถูกต้อง: เลือกไฟล์ที่มีนามสกุล .cha",
      invalidFile: "ไฟล์ .cha ไม่ถูกต้อง",
      previewTitle: "ตัวอย่างบทถอดเสียง",
      previewOnly: "แสดงตัวอย่างเท่านั้น",
      noTranscriptTitle: "ยังไม่มีบทถอดเสียง",
      noTranscriptBody: "เพิ่มแหล่งข้อมูลก่อน แล้วไปต่อที่การตั้งค่าบทถอดเสียงและการทบทวนของนักบำบัด",
      back: "กลับไปรายละเอียดเซสชัน",
      continue: "ไปต่อที่ตั้งค่าบทถอดเสียง",
      audioBody:
        "ยังอัปโหลดไฟล์เสียงที่มีอยู่แล้วไม่ได้ ให้บันทึกเสียงในเบราว์เซอร์เพื่อถอดเสียง หรืออัปโหลดไฟล์ .cha หรือวางบทถอดเสียงที่มีอยู่",
      quickDemo: "ตัวอย่างสำหรับสาธิต:",
      thaiSample: "ตัวอย่างภาษาไทย",
      thaiSampleTitle: "ใส่บทสนทนาตัวอย่างภาษาไทยสำหรับสาธิต",
      englishSample: "ตัวอย่างภาษาอังกฤษ",
      englishSampleTitle: "ใส่บทสนทนาตัวอย่างภาษาอังกฤษ",
      chaFileLabel: "ไฟล์บทถอดเสียง CHA",
      chaTextLabel: "ข้อความบทถอดเสียง CHA",
      pasteTextLabel: "ข้อความบทถอดเสียงที่วาง",
      importWarnings: "คำเตือนจากการนำเข้า",
      chatValidation: "การตรวจรูปแบบ CHAT",
      saveTranscript: "บันทึกบทถอดเสียง",
    },
    setup: {
      body: "กำหนดวิธีทบทวนบทถอดเสียง ช่องเหล่านี้ไม่ได้ปลดล็อกการวิเคราะห์ ยังต้องตรวจคุณภาพและให้นักบำบัดรับรองในขั้นถัดไป",
      speakerLabels: "ป้ายชื่อผู้พูด",
      metadata: "ข้อมูลประกอบของเซสชัน",
      language: "ภาษา",
      languages: { eng: "อังกฤษ", tha: "ไทย", mixed: "ตัวอย่างหลายภาษา" },
      sampleType: "ประเภทตัวอย่าง",
      sampleTypes: { conversation: "บทสนทนา", play: "ปฏิสัมพันธ์ระหว่างเล่น", narrative: "การเล่าเรื่อง" },
      requirements: "ข้อกำหนดในการทบทวน",
      reviewSpeakerLabels: "ฉันจะทบทวนป้ายชื่อผู้พูดและถ้อยคำในบทถอดเสียงก่อนรับรอง",
      reviewFeatureLock:
        "ฉันเข้าใจว่าการสกัดค่าทางภาษาจะล็อกอยู่ จนกว่าจะทบทวนบทถอดเสียง ตรวจคุณภาพ และรับรองเสร็จ",
      back: "กลับไปแหล่งข้อมูล",
      continue: "ไปต่อที่ตรวจทานและเริ่ม",
    },
    review: {
      body: "ตรวจสรุป อ่านประกาศความเป็นส่วนตัว แล้วเข้าสู่ขั้นตอนทบทวนบทถอดเสียง",
      sessionSummary: "สรุปเซสชัน",
      workflowSummary: "สรุปขั้นตอน",
      childClient: "เด็ก/ผู้รับบริการ",
      date: "วันที่",
      time: "เวลา",
      setting: "สถานที่",
      duration: "ระยะเวลา",
      clinician: "นักบำบัด",
      sourceType: "ประเภทแหล่งข้อมูล",
      transcriptSource: "แหล่งบทถอดเสียง",
      language: "ภาษา",
      sampleType: "ประเภทตัวอย่าง",
      goals: "เป้าหมาย",
      notSet: "ยังไม่ระบุ",
      sourceReady: "พร้อมให้นักบำบัดทบทวน",
      sourceNotReady: "ยังต้องมีข้อมูลที่พร้อมเป็นบทถอดเสียง",
      safetyNote:
        "ข้อมูลเสียงไม่ถูกเก็บในที่เก็บถาวรของเบราว์เซอร์ ผลการถอดเสียงอัตโนมัติขั้นทดลองต้องให้นักบำบัดทบทวนก่อนรับรองบทถอดเสียง สกัดค่าทางภาษา หรือใช้ในรายงาน",
      asrWarning:
        "การอัปโหลดเสียงและการถอดเสียงอัตโนมัติยังอยู่ในขั้นทดลอง ให้เริ่มทบทวนบทถอดเสียงเมื่อมีร่างบทถอดเสียงจริงแล้วเท่านั้น",
      back: "กลับไปตั้งค่าบทถอดเสียง",
      save: "บันทึกเซสชัน",
      start: "เริ่มทบทวนบทถอดเสียง",
    },
  },
});
