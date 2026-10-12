"use client";

import type { Dispatch, SetStateAction } from "react";
import type { RecordingMetadata } from "@/components/browser-audio-recorder";
import { SafetyNote } from "@/components/workbench-ui";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import {
  ReviewSummaryCard,
  SessionProgressCard,
  WorkflowStatus,
} from "@/features/sessions/intake/session-intake-components";
import { SessionIntakeSteps } from "@/features/sessions/intake/session-intake-steps";
import { intakeMessages } from "@/features/sessions/intake/intake.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";
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

const intakeStepOrder: SessionIntakeStepId[] = ["details", "source", "setup", "review"];

export function SessionIntakeView({ model }: { model: SessionIntakeViewModel }) {
  const { sessionContext, intakeStep, selectedSource, state, backendUnavailable } = model;
  const t = useMessages(intakeMessages);
  const safety = useSafetyCopy();
  // A step is ticked when its own inputs are in, not because a later step is open.
  const stepDone: Record<SessionIntakeStepId, boolean> = {
    details: model.caseConsent === "granted" && model.sessionDetailsComplete,
    source: model.sourceReadyForReview,
    setup: model.transcriptSetupComplete,
    review: state.transcriptReady,
  };
  const stepNumber = intakeStepOrder.indexOf(intakeStep) + 1;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-6">
        <SessionContextHeader
          title={t.view.title}
          description={t.view.description}
          meta={t.view.meta}
          context={sessionContext}
        />
        {/* A slim bar, not a second numbered rail: the session rail above already has one. */}
        <div role="group" aria-label={t.view.stepsLabel}>
          <p className="text-sm font-semibold text-ink">
            <span className="text-brand-strong">{t.view.stepOf(stepNumber, intakeStepOrder.length)}</span>
            <span aria-hidden="true" className="text-ink-subtle"> · </span>
            {t.steps[intakeStep]}
          </p>
          <ol className="mt-2 flex gap-1.5" role="list">
            {intakeStepOrder.map((id) => (
              <li
                key={id}
                aria-current={id === intakeStep ? "step" : undefined}
                className={`h-1.5 flex-1 rounded-full ${id === intakeStep ? "bg-brand" : stepDone[id] ? "bg-sky-strong" : "bg-line-strong"}`}
              >
                <span className="sr-only">
                  {t.steps[id]} ({id === intakeStep ? t.view.stepStates.current : stepDone[id] ? t.view.stepStates.complete : t.view.stepStates.available})
                </span>
              </li>
            ))}
          </ol>
        </div>
        <SessionIntakeSteps model={model} />

        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
        <SafetyNote>{safety.NON_DIAGNOSTIC_CLAIM} {t.view.finalNote}</SafetyNote>
      </div>
      <div className="space-y-6">
        <ReviewSummaryCard title={t.view.currentIntake} rows={[
          { label: t.view.rowStep, value: t.steps[intakeStep] },
          { label: t.view.rowSource, value: t.sources[selectedSource] },
          { label: t.view.rowTranscriptStatus, value: state.transcriptReady ? t.view.readyForReview : t.view.pending },
        ]} />
        <SessionProgressCard state={state} />
      </div>
    </div>
  );
}
