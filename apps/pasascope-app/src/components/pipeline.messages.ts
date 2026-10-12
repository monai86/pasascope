import type { PipelineState } from "@/components/pipeline-progress-bar";
import { defineMessages } from "@/i18n/messages";
import { EVIDENCE_REVIEW_NOUN } from "@/lib/workflow-glossary";

type PipelineCopy = {
  title: string;
  stage: (current: number, total: number, label: string) => string;
  progress: (label: string) => string;
  stages: Record<PipelineState, string>;
};

export const pipelineMessages = defineMessages<PipelineCopy>({
  en: {
    title: "Pipeline Status",
    stage: (current, total, label) => `Stage ${current} of ${total}: ${label}`,
    progress: (label) => `Pipeline Progress: ${label}`,
    stages: {
      awaiting_consent: "Consent",
      ready_for_audio: "Ready",
      uploading: "Upload",
      transcribing: "ASR",
      cha_generating: "CHA",
      review_required: "Review",
      ml_pending: EVIDENCE_REVIEW_NOUN,
      report_ready: "Report",
    },
  },
  th: {
    title: "สถานะของงาน",
    stage: (current, total, label) => `ขั้นที่ ${current} จาก ${total}: ${label}`,
    progress: (label) => `ความคืบหน้าของงาน: ${label}`,
    stages: {
      awaiting_consent: "ความยินยอม",
      ready_for_audio: "พร้อม",
      uploading: "อัปโหลด",
      transcribing: "ถอดเสียง",
      cha_generating: "ไฟล์ CHA",
      review_required: "ทบทวน",
      ml_pending: "ทบทวนหลักฐาน",
      report_ready: "รายงาน",
    },
  },
});
