import type { SessionView } from "@/features/sessions/state/session-view";
import { defineMessages } from "@/i18n/messages";
import { EXTRACT_FEATURES_ACTION, GENERATE_REPORT_ACTION } from "@/lib/workflow-glossary";

type SessionCopy = {
  views: Record<SessionView, string>;
  header: {
    contextLabel: string;
    viewsLabel: string;
    casesCrumb: string;
    stepComplete: string;
    /** Chat shell: the way back from a full page to the session's conversation. */
    backToConversation: string;
    /** Chat shell: what the first step is called, where the conversation replaces Intake. */
    conversation: string;
    unavailable: string;
    details: string;
    fields: { case: string; session: string; source: string; consent: string; status: string; connection: string };
    connection: { backend: string; local_draft: string; unavailable: string };
    consent: (status: string) => string;
  };
  guide: { label: string };
  progress: {
    title: string;
    steps: Record<SessionView, string>;
    done: string;
    notYet: string;
    next: Record<Exclude<SessionView, "intake">, string>;
  };
  transcript: {
    title: string;
    description: string;
    goToReport: string;
    guide: {
      extracted: string;
      continueToFindings: string;
      attested: string;
      extract: string;
      extracting: string;
      unsaved: string;
      qaNotRun: string;
      qaFailed: string;
      readyToAttest: string;
      readyToAnalyze: string;
      analyze: string;
      attest: string;
      attesting: string;
    };
    asrCaution: string;
    importWarnings: string;
    mode: { label: string; audio: string; classic: string; chat: string };
    attestedNote: string;
    notAttestedNote: string;
    continueToAttestation: string;
    readiness: {
      summary: string;
      locked: string;
      ready: string;
      regionLabel: string;
      lockedTitle: string;
      readyTitle: string;
      readyBody: string;
      generate: string;
      done: string;
      notDone: string;
      checklist: { saved: string; qa: string; attested: string; extracted: string };
      blocked: { unsaved: string; qaNotRun: string; qaFailed: string; attestFailed: string; notAttested: string; noFeatures: string };
    };
    requirements: { summary: string; body: string };
  };
};

const consentTh: Record<string, string> = {
  granted: "ให้ความยินยอมแล้ว",
  pending: "รอความยินยอม",
  withdrawn: "ถอนความยินยอมแล้ว",
};

export const sessionMessages = defineMessages<SessionCopy>({
  en: {
    views: { intake: "Intake", transcript: "Transcript", findings: "Findings", report: "Report" },
    header: {
      contextLabel: "Session context",
      viewsLabel: "Session views",
      casesCrumb: "Cases",
      stepComplete: "Step complete",
      backToConversation: "Back to the conversation",
      conversation: "Conversation",
      unavailable: "Unavailable",
      details: "Details",
      fields: { case: "Case", session: "Session", source: "Source", consent: "Consent", status: "Status", connection: "Connection" },
      connection: { backend: "Connected", local_draft: "Offline draft", unavailable: "Offline" },
      consent: (status) => `Consent ${status.toLowerCase()}`,
    },
    guide: { label: "What to do next" },
    progress: {
      title: "Session progress",
      steps: { intake: "Transcript added", transcript: "Transcript attested", findings: "Features extracted", report: "Report signed" },
      done: "Done",
      notYet: "Not yet",
      next: { transcript: "Review Transcript", findings: "Open Findings", report: "Open Report" },
    },
    transcript: {
      title: "Review Transcript",
      description: "Confirm speaker labels and transcript quality before report generation.",
      goToReport: "Go to report",
      guide: {
        extracted: "Features are extracted from the attested transcript. Review them in Findings.",
        continueToFindings: "Continue to Findings",
        attested: "The transcript is reviewed and attested. Next, we'll extract the language-sample features.",
        extract: EXTRACT_FEATURES_ACTION,
        extracting: "Extracting...",
        unsaved: "Check the speaker labels and wording below, then save the draft.",
        qaNotRun: "The draft is saved. Run QA on the transcript before attesting it.",
        qaFailed: "QA found issues that block attestation. Fix them, save, and run QA again.",
        readyToAttest: "The draft is saved and QA is complete. Attest the transcript to confirm your review.",
        attest: "Attest this transcript",
        readyToAnalyze: "The transcript is saved. Analyse it to see the language-sample measures.",
        analyze: "Analyse this transcript",
        attesting: "Recording attestation...",
      },
      asrCaution: "This transcript was made automatically and can be wrong. Check the words, the times and who is speaking before you use it.",
      importWarnings: "Import notes",
      mode: { label: "How to work on the transcript", audio: "Listen and assign speakers", classic: "Edit line by line", chat: "CHAT text" },
      attestedNote: "This transcript is attested.",
      notAttestedNote: "When the speakers and wording are correct, save the transcript, run QA and attest it.",
      continueToAttestation: "Continue to save, QA and attestation",
      readiness: {
        summary: "Report readiness",
        locked: "Locked",
        ready: "Ready",
        regionLabel: "Report generation readiness",
        lockedTitle: "Report generation is locked",
        readyTitle: "Ready to generate report",
        readyBody: "Transcript review is complete. Generate the therapist-editable draft report.",
        generate: GENERATE_REPORT_ACTION,
        done: "(done)",
        notDone: "(not done)",
        checklist: { saved: "Draft saved", qa: "QA completed", attested: "Therapist attested", extracted: "Features extracted" },
        blocked: {
          unsaved: "Save the transcript draft before generating a report.",
          qaNotRun: "Run transcript QA before generating a report.",
          qaFailed: "Resolve transcript QA issues before generating a report.",
          attestFailed: "Attestation did not finish. Try Attest transcript again before generating a report.",
          notAttested: "Click Attest transcript before generating a report.",
          noFeatures: "Extract language-sample features before generating a report.",
        },
      },
      requirements: {
        summary: "Review requirements",
        body: "Report generation requires a saved draft, completed QA, therapist attestation, and extracted language-sample features. Editing after attestation resets these gates.",
      },
    },
  },
  th: {
    views: { intake: "รับข้อมูล", transcript: "บทถอดเสียง", findings: "ผลการวิเคราะห์", report: "รายงาน" },
    header: {
      contextLabel: "ข้อมูลของเซสชัน",
      viewsLabel: "ขั้นตอนของเซสชัน",
      casesCrumb: "เคส",
      stepComplete: "ขั้นตอนนี้เสร็จแล้ว",
      backToConversation: "กลับไปที่บทสนทนา",
      conversation: "บทสนทนา",
      unavailable: "ไม่มีข้อมูล",
      details: "รายละเอียด",
      fields: { case: "เคส", session: "เซสชัน", source: "แหล่งข้อมูล", consent: "ความยินยอม", status: "สถานะ", connection: "การเชื่อมต่อ" },
      connection: { backend: "เชื่อมต่อแล้ว", local_draft: "ร่างในเครื่อง", unavailable: "ออฟไลน์" },
      consent: (status) => consentTh[status.toLowerCase()] ?? `ความยินยอม: ${status}`,
    },
    guide: { label: "สิ่งที่ต้องทำต่อไป" },
    progress: {
      title: "ความคืบหน้าของเซสชัน",
      steps: { intake: "เพิ่มบทถอดเสียงแล้ว", transcript: "รับรองบทถอดเสียงแล้ว", findings: "สกัดค่าทางภาษาแล้ว", report: "ลงนามรายงานแล้ว" },
      done: "เสร็จแล้ว",
      notYet: "ยังไม่เสร็จ",
      next: { transcript: "ทบทวนบทถอดเสียง", findings: "เปิดผลการวิเคราะห์", report: "เปิดรายงาน" },
    },
    transcript: {
      title: "ทบทวนบทถอดเสียง",
      description: "ตรวจรหัสผู้พูดและคุณภาพของบทถอดเสียงก่อนสร้างรายงาน",
      goToReport: "ไปที่รายงาน",
      guide: {
        extracted: "สกัดค่าทางภาษาจากบทถอดเสียงที่รับรองแล้วเรียบร้อย ดูผลได้ที่ผลการวิเคราะห์",
        continueToFindings: "ไปที่ผลการวิเคราะห์",
        attested: "บทถอดเสียงทบทวนและรับรองแล้ว ขั้นต่อไปคือสกัดค่าทางภาษาจากตัวอย่างภาษา",
        extract: "สกัดค่าทางภาษาจากตัวอย่างภาษา",
        extracting: "กำลังสกัดค่า...",
        unsaved: "ตรวจรหัสผู้พูดและถ้อยคำด้านล่าง แล้วบันทึกร่าง",
        qaNotRun: "บันทึกร่างแล้ว ให้ตรวจคุณภาพบทถอดเสียงก่อนรับรอง",
        qaFailed: "การตรวจคุณภาพพบปัญหาที่ทำให้ยังรับรองไม่ได้ แก้ไข บันทึก แล้วตรวจคุณภาพอีกครั้ง",
        readyToAttest: "บันทึกร่างและตรวจคุณภาพเรียบร้อยแล้ว รับรองบทถอดเสียงเพื่อยืนยันว่าคุณทบทวนแล้ว",
        attest: "รับรองบทถอดเสียงนี้",
        readyToAnalyze: "บันทึกบทถอดเสียงแล้ว กดวิเคราะห์เพื่อดูค่าทางภาษาของตัวอย่าง",
        analyze: "วิเคราะห์บทถอดเสียงนี้",
        attesting: "กำลังบันทึกการรับรอง...",
      },
      asrCaution: "บทถอดเสียงนี้ทำโดยอัตโนมัติและอาจผิดได้ ตรวจถ้อยคำ เวลา และผู้พูดก่อนนำไปใช้",
      importWarnings: "หมายเหตุจากการนำเข้า",
      mode: { label: "วิธีทำงานกับบทถอดเสียง", audio: "ฟังและระบุผู้พูด", classic: "แก้ทีละบรรทัด", chat: "ข้อความ CHAT" },
      attestedNote: "บทถอดเสียงนี้รับรองแล้ว",
      notAttestedNote: "เมื่อผู้พูดและถ้อยคำถูกต้องแล้ว ให้บันทึก ตรวจคุณภาพ แล้วรับรองบทถอดเสียง",
      continueToAttestation: "ไปบันทึก ตรวจคุณภาพ และรับรอง",
      readiness: {
        summary: "ความพร้อมของรายงาน",
        locked: "ยังล็อกอยู่",
        ready: "พร้อม",
        regionLabel: "ความพร้อมในการสร้างรายงาน",
        lockedTitle: "ยังสร้างรายงานไม่ได้",
        readyTitle: "พร้อมสร้างรายงาน",
        readyBody: "ทบทวนบทถอดเสียงครบแล้ว สร้างร่างรายงานที่นักบำบัดแก้ไขได้",
        generate: "สร้างร่างรายงาน",
        done: "(เสร็จแล้ว)",
        notDone: "(ยังไม่เสร็จ)",
        checklist: { saved: "บันทึกร่างแล้ว", qa: "ตรวจคุณภาพแล้ว", attested: "นักบำบัดรับรองแล้ว", extracted: "สกัดค่าทางภาษาแล้ว" },
        blocked: {
          unsaved: "บันทึกร่างบทถอดเสียงก่อนสร้างรายงาน",
          qaNotRun: "ตรวจคุณภาพบทถอดเสียงก่อนสร้างรายงาน",
          qaFailed: "แก้ปัญหาที่พบจากการตรวจคุณภาพก่อนสร้างรายงาน",
          attestFailed: "การรับรองยังไม่สำเร็จ กดรับรองบทถอดเสียงอีกครั้งก่อนสร้างรายงาน",
          notAttested: "รับรองบทถอดเสียงก่อนสร้างรายงาน",
          noFeatures: "สกัดค่าทางภาษาจากตัวอย่างภาษาก่อนสร้างรายงาน",
        },
      },
      requirements: {
        summary: "เงื่อนไขก่อนสร้างรายงาน",
        body: "การสร้างรายงานต้องมีร่างที่บันทึกแล้ว การตรวจคุณภาพที่เสร็จแล้ว การรับรองของนักบำบัด และค่าทางภาษาที่สกัดแล้ว หากแก้ไขหลังรับรอง เงื่อนไขเหล่านี้จะเริ่มใหม่",
      },
    },
  },
});
