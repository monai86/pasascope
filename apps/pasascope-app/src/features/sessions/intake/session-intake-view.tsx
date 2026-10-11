"use client";

import type { Dispatch, SetStateAction } from "react";
import type { RecordingMetadata } from "@/components/browser-audio-recorder";
import { SafetyNote } from "@/components/workbench-ui";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import {
  ReviewSummaryCard,
  SessionProgressCard,
  sourceSummaryLabel,
  WorkflowStatus,
} from "@/features/sessions/intake/session-intake-components";
import { SessionIntakeSteps } from "@/features/sessions/intake/session-intake-steps";
import { NON_DIAGNOSTIC_CLAIM } from "@/lib/clinical-safety-copy";
import type { WorkflowSource, WorkflowState } from "@/lib/workflow";

export type SessionIntakeStepId = "details" | "source" | "setup" | "review";
export type SessionIntakeSource = "recording" | "audio" | "cha" | "paste";

type SessionDetailsDraft = {
  childClient: string;
  sessionDate: string;
  sessionTime: string;
  setting: string;
  durationMinutes: string;
  clinician: string;
  sessionGoals: string;
};

type TranscriptSetupDraft = {
  speakerLabels: string;
  sessionMetadata: string;
  language: string;
  sampleType: string;
  reviewSpeakerLabels: boolean;
  reviewFeatureLock: boolean;
};

type RecordedAudio = { blob: Blob; metadata: RecordingMetadata } | null;
type UploadStep = "idle" | "confirm" | "uploading" | "polling" | "done" | "error";

export type SessionIntakeViewModel = {
  sessionContext: SessionContext;
  pipelineStatusValue: string;
  intakeStep: SessionIntakeStepId;
  setIntakeStep: Dispatch<SetStateAction<SessionIntakeStepId>>;
  caseConsent: string;
  intakeError: string;
  setIntakeError: Dispatch<SetStateAction<string>>;
  consentChecked: boolean;
  setConsentChecked: Dispatch<SetStateAction<boolean>>;
  consentSigner: string;
  setConsentSigner: Dispatch<SetStateAction<string>>;
  consentDate: string;
  setConsentDate: Dispatch<SetStateAction<string>>;
  consentNotes: string;
  setConsentNotes: Dispatch<SetStateAction<string>>;
  busy: boolean;
  handleGrantConsent: () => void | Promise<void>;
  sessionDetails: SessionDetailsDraft;
  setSessionDetails: Dispatch<SetStateAction<SessionDetailsDraft>>;
  sessionDetailsComplete: boolean;
  transcriptSetupComplete: boolean;
  selectedSource: SessionIntakeSource;
  setSelectedSource: Dispatch<SetStateAction<SessionIntakeSource>>;
  state: WorkflowState;
  setState: Dispatch<SetStateAction<WorkflowState>>;
  recordedAudio: RecordedAudio;
  setRecordedAudio: Dispatch<SetStateAction<RecordedAudio>>;
  uploadStep: UploadStep;
  setUploadStep: Dispatch<SetStateAction<UploadStep>>;
  handleRecordingMetadata: (metadata: RecordingMetadata) => void;
  handleRecordingReady: (blob: Blob, metadata: RecordingMetadata) => void;
  handleUploadForTranscription: () => void | Promise<void>;
  transJobStatus: string;
  transJobMessage: string;
  transJobRequestedProvider?: string;
  transJobActualProvider?: string;
  backendUnavailable: boolean;
  draftTranscript: string;
  setDraftTranscript: Dispatch<SetStateAction<string>>;
  setSourceFilename: Dispatch<SetStateAction<string | undefined>>;
  intakeWarnings: string[];
  setIntakeWarnings: Dispatch<SetStateAction<string[]>>;
  intakeValidationIssues: string[];
  setIntakeValidationIssues: Dispatch<SetStateAction<string[]>>;
  handleTranscriptSubmit: (source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">) => void | Promise<void>;
  transcriptLines: string[];
  transcriptSetup: TranscriptSetupDraft;
  setTranscriptSetup: Dispatch<SetStateAction<TranscriptSetupDraft>>;
  sourceReadyForReview: boolean;
  canStartTranscriptReview: boolean;
  saveSessionIntakeDraft: () => WorkflowState;
  handleAnalyze: () => void | Promise<void>;
  handleGenerateReport: () => void | Promise<void>;
  router: { push: (href: string) => void };
};

const sessionIntakeStepLabels: Array<{ id: SessionIntakeStepId; title: string; helper: string }> = [
  { id: "details", title: "Session Details", helper: "Set the session context before adding source material." },
  { id: "source", title: "Source Material", helper: "Record, upload, or paste the material for therapist review." },
  { id: "setup", title: "Transcript Setup", helper: "Define labels, metadata, and review requirements." },
  { id: "review", title: "Review & Start", helper: "Confirm safety notices before opening transcript review." },
];

export function SessionIntakeView({ model }: { model: SessionIntakeViewModel }) {
  const { sessionContext, intakeStep, selectedSource, state, backendUnavailable } = model;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-6">
        <SessionContextHeader
          title="Session Intake"
          description="Capture session context, prepare source material, and route the workflow into therapist transcript review without weakening the existing review and attestation gates."
          meta={["Audio upload requires explicit confirmation", "ASR remains experimental"]}
          context={sessionContext}
        />
        <SessionIntakeSteps model={model} />

        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
        <SafetyNote>{NON_DIAGNOSTIC_CLAIM} Transcript must be reviewed before report use.</SafetyNote>
      </div>
      <div className="space-y-6">
        <ReviewSummaryCard title="Current intake" rows={[
          { label: "Step", value: sessionIntakeStepLabels.find((item) => item.id === intakeStep)?.title ?? "Session Details" },
          { label: "Source", value: sourceSummaryLabel(selectedSource) },
          { label: "Transcript status", value: state.transcriptReady ? "Ready for review" : "Pending" },
        ]} />
        <SessionProgressCard state={state} />
      </div>
    </div>
  );
}
