"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiBlob } from "@/lib/api";
import {
  DRAFT_ASR_TRANSCRIPT_LABEL,
  THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE,
} from "@/lib/clinical-safety-copy";
import { FEATURE_EXTRACTION_NOUN } from "@/lib/workflow-glossary";

import type { RecordingMetadata } from "@/components/browser-audio-recorder";
import { useBackendAvailability } from "@/components/backend-availability-banner";
import {
  backendTranscriptLines,
  buildBasicChatExport,
  buildFeatureSignals,
  createBackendSession,
  ensureWorkflowSession,
  classifyWorkflowLoadFailure,
  createIdentityScopedWorkflowState,
  createInitialWorkflowState,
  defaultTranscript,
  evaluateTranscriptQa,
  exportReviewedCha,
  getBackendCase,
  getBackendSession,
  getBackendSessionTranscript,
  getBackendTranscript,
  loadWorkflowState,
  prepareTranscriptIntake,
  saveWorkflowState,
  summarizeAnalysis,
  type TranscriptLine,
  type WorkflowSource,
  type WorkflowState,
  getSessionAudioFiles,
  uploadAudioBlobToBackend,
  startBackendTranscriptionJob,
  pollTranscriptionJob,
  findAvailableTranscriptionProvider,
  transcriptionWaitBudgetMs
} from "@/lib/workflow";
import {
  acknowledgeSessionCues,
  generateAiReview,
  generateMlDecisionSupport,
  getAiReview,
  getBackendFeatureDefinitions,
  getBackendSessionFeatures,
  getMlDecisionSupport,
  getMlReadiness,
  updateProfileEvidenceReview,
  updateCueReview,
} from "@/services/adapters/analysis-adapter";
import { canApplyMlDecisionSupportSettlement, canApplyTranscriptSaveSettlement, canSettleWorkflowRequest, derivePipelineStatus, sessionWorkflowReducer } from "@/features/sessions/state/session-workflow-reducer";
import { sessionWorkflowService } from "@/features/sessions/services/session-workflow-service";
import { resolveSessionHref, resolveWorkspaceFeature, type SessionView } from "@/features/sessions/state/session-view";
import { sessionCompletion } from "@/features/sessions/state/session-completion";
import { getSessionTranscriptionJob, updateBackendSessionNotes } from "@/features/sessions/chat/chat-api";
import { assignUnknownSpeakers } from "@/features/sessions/chat/chat-thread-model";
import type { SessionContext } from "@/features/sessions/components/session-context-header";
import { SessionWorkflowView, type SessionWorkflowViewModel } from "@/features/sessions/components/session-workspace-view";
import { useAppMode } from "@/lib/app-mode";

export type SessionWorkspaceProps = {
  sessionId?: string;
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
  view?: SessionView;
  mode?: string;
};

type SessionWorkspaceIdentityProps = Omit<SessionWorkspaceProps, "view"> & {
  view?: "transcript" | "findings" | "chat";
};

export function SessionWorkflowWorkspace(props: SessionWorkspaceProps) {
  const identityKey = JSON.stringify([
    props.sessionId ?? "",
    props.caseId ?? "",
    props.transcriptId ?? "",
    props.reportId ?? "",
  ]);
  const view = resolveWorkspaceFeature(props.view);
  return <SessionWorkspaceIdentityScope key={identityKey} {...props} view={view} />;
}

/** The same controller, presented as one conversation instead of separate step screens. */
export function SessionChatWorkspace(props: Omit<SessionWorkspaceProps, "view">) {
  const identityKey = JSON.stringify([
    props.sessionId ?? "",
    props.caseId ?? "",
    props.transcriptId ?? "",
    props.reportId ?? "",
  ]);
  return <SessionWorkspaceIdentityScope key={identityKey} {...props} view="chat" />;
}

function SessionWorkspaceIdentityScope({ sessionId, caseId, transcriptId, reportId, view = "chat", mode }: SessionWorkspaceIdentityProps) {
  const model = useSessionWorkspace({ sessionId, caseId, transcriptId, reportId, view, mode });
  return <SessionWorkflowView model={model} />;
}

/**
 * Identity-scoped workflow controller. It owns request sequencing, persistence,
 * and mutations; visual rendering stays in SessionWorkflowView and the feature
 * views so transport state cannot leak into layout components.
 */
export function useSessionWorkspace({ sessionId, caseId, transcriptId, reportId, view = "chat", mode }: SessionWorkspaceIdentityProps): SessionWorkflowViewModel {
  const { openGates } = useAppMode();
  const hasLocator = Boolean(sessionId || transcriptId || caseId || reportId);
  const [state, setState] = useState<WorkflowState>(() => hasLocator
    ? createIdentityScopedWorkflowState({ workflowLoading: true, statusMessage: "Loading persisted workflow..." })
    : createInitialWorkflowState());
  const workflowRevisionRef = useRef(0);
  const activeTranscriptSaveRevisionRef = useRef<number | null>(null);
  const workflowStateRef = useRef(state);
  const viewRef = useRef(view);
  const resumeTranscriptionRef = useRef<(jobId: string, targetSessionId: string) => void>(() => {});
  const [busy, setBusy] = useState(false);

  useEffect(() => () => {
    workflowRevisionRef.current += 1;
    activeTranscriptSaveRevisionRef.current = null;
  }, []);

  useEffect(() => {
    workflowStateRef.current = state;
  }, [state]);

  // Read by the load below without making it run again when they change.
  useEffect(() => {
    viewRef.current = view;
    resumeTranscriptionRef.current = (jobId, targetSessionId) => {
      setTransJobId(jobId);
      setTransJobStatus("processing");
      setTransJobMessage("");
      setUploadStep("polling");
      setBusy(true);
      void pollUntilComplete(jobId, RESUMED_TRANSCRIPTION_WAIT_MS, targetSessionId);
    };
  });
  const [draftTranscript, setDraftTranscript] = useState(hasLocator ? "" : defaultTranscript);
  const [editorLines, setEditorLines] = useState<TranscriptLine[]>([]);
  const [sourceFilename, setSourceFilename] = useState<string | undefined>();
  const [intakeError, setIntakeError] = useState("");
  const [recordedAudio, setRecordedAudio] = useState<{ blob: Blob; metadata: RecordingMetadata; extension?: string } | null>(null);
  const [audioFileError, setAudioFileError] = useState<"unsupported" | undefined>();
  const [sessionNotes, setSessionNotes] = useState("");
  const [sessionSummary, setSessionSummary] = useState<{
    caseCode?: string;
    ageMonths?: number;
    language?: string;
    sessionDate?: string;
  }>({});
  const [uploadStep, setUploadStep] = useState<
    "idle" | "confirm" | "uploading" | "polling" | "done" | "error"
  >("idle");
  const [transJobId, setTransJobId] = useState<string | undefined>();
  const [transJobStatus, setTransJobStatus] = useState<string>("queued");
  const [transJobMessage, setTransJobMessage] = useState<string>("");
  const [caseConsent, setCaseConsent] = useState<string>("granted");
  const [isHydrated, setIsHydrated] = useState(false);

  const handleRecordingReady = (blob: Blob, metadata: RecordingMetadata) => {
    setRecordedAudio({ blob, metadata });
    setUploadStep("confirm");
  };

  const [audioUrl, setAudioUrl] = useState<string | undefined>(undefined);
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const router = useRouter();

  const pipelineStatusValue = useMemo(() => {
    return derivePipelineStatus(state, caseConsent, uploadStep);
  }, [caseConsent, state, uploadStep]);

  useEffect(() => {
    let cancelled = false;
    if (!hasLocator) {
      const stored = loadWorkflowState();
      setState((current) => sessionWorkflowReducer(current, { type: "session-identity-changed", state: stored }));
      setDraftTranscript(stored.transcriptText || (mode === "paste" || mode === "cha" ? "" : defaultTranscript));
      setEditorLines(stored.transcriptLines);
      setSourceFilename(stored.sourceFilename);
      setIsHydrated(true);
      return;
    }

    const loadingState = saveWorkflowState(sessionWorkflowReducer(
      createIdentityScopedWorkflowState(),
      { type: "request-started", message: "Loading persisted workflow..." },
    ));
    setBackendUnavailable(false);
    setState(loadingState);
    setAudioUrl(undefined);
    setDraftTranscript("");
    setEditorLines([]);
    setSourceFilename(undefined);
    void Promise.resolve().then(async () => {
      // React Strict Mode replays effects in development. Deferring the request
      // one microtask lets the replay cleanup cancel the discarded run before
      // it can issue duplicate clinical-workflow reads.
      if (cancelled) return;
      try {
        const loaded = sessionId
          ? await sessionWorkflowService.load({ sessionId, transcriptId, reportId })
          : undefined;
        const backendSession = loaded?.session;
        const backendReport = loaded?.report;
        const resolvedTranscriptId = transcriptId ?? backendSession?.transcript_id;
        const transcript = loaded?.transcript ?? (resolvedTranscriptId
          ? await getBackendTranscript(resolvedTranscriptId)
          : backendSession
            ? await getBackendSessionTranscript(backendSession.session_id).catch(() => undefined)
            : undefined);
        // The conversation stays on one page, so a job started before a reload
        // is picked up again instead of asking for the audio a second time.
        const unfinishedJob = viewRef.current === "chat" && !transcript && backendSession
          ? await getSessionTranscriptionJob(backendSession.session_id).catch(() => null)
          : null;
        const resolvedCaseId = caseId ?? backendSession?.case_id ?? transcript?.case_id;
        const childCase = resolvedCaseId ? await getBackendCase(resolvedCaseId) : undefined;
        if (childCase && !cancelled) {
          setCaseConsent(childCase.consent_status ?? "pending");
        }
        if (!cancelled) {
          setSessionNotes(backendSession?.notes ?? "");
          setSessionSummary({
            caseCode: childCase?.child_code,
            ageMonths: childCase?.age_months,
            language: childCase?.language,
            sessionDate: backendSession?.session_date,
          });
        }
        const lines = transcript ? backendTranscriptLines(transcript) : [];
        const parsed = transcript?.raw_text ? prepareTranscriptIntake("cha-upload", transcript.raw_text) : undefined;

        const audioFiles = sessionId || backendSession?.session_id
          ? await getSessionAudioFiles(sessionId ?? backendSession!.session_id).catch(() => [])
          : [];
        const primaryAudio = Array.isArray(audioFiles)
          ? audioFiles.find((f) => f.upload_status === "uploaded")
          : undefined;
        const resolvedAudioUrl = primaryAudio
          ? await createBackendAudioObjectUrl(primaryAudio.audio_file_id).catch(() => undefined)
          : undefined;
        const resolvedSessionId = backendSession?.session_id ?? transcript?.session_id ?? sessionId;
        const mlReadiness = transcript?.transcript_id
          ? await getMlReadiness(transcript.transcript_id).catch(() => undefined)
          : undefined;
        const mlDecisionSupport = resolvedSessionId
          ? await getMlDecisionSupport(resolvedSessionId).catch(() => undefined)
          : undefined;
        const aiReview = resolvedSessionId
          ? await getAiReview(resolvedSessionId).catch(() => undefined)
          : undefined;
        const backendFeatures = resolvedSessionId && backendSession?.feature_set_id
          ? await getBackendSessionFeatures(resolvedSessionId).catch(() => undefined)
          : undefined;
        const featureDefinitions = backendFeatures
          ? await getBackendFeatureDefinitions().catch(() => [])
          : [];
        const analysisSummary = backendFeatures
          ? summarizeAnalysis({
            status: transcript?.qa_status,
            qa_status: transcript?.qa_status,
            issues: (transcript?.qa_issues ?? []).map((issue) => typeof issue === "string" ? issue : issue.message ?? "Transcript QA issue")
          }, backendFeatures)
          : undefined;
        const featureSignals = buildFeatureSignals(backendFeatures, featureDefinitions);
        const findingsAreStale = backendFeatures?.review_status === "stale";

        if (cancelled) {
          if (resolvedAudioUrl?.startsWith("blob:")) {
            URL.revokeObjectURL(resolvedAudioUrl);
          }
          return;
        }
        const emptyState = createIdentityScopedWorkflowState();
        const hydrated = saveWorkflowState({
          ...emptyState,
          sessionId: resolvedSessionId,
          caseId: resolvedCaseId,
          caseInfo: {
            caseId: resolvedCaseId,
            clientLabel: childCase?.nickname ?? childCase?.child_code ?? ""
          },
          childName: childCase?.nickname ?? childCase?.child_code ?? "",
          backendSessionId: backendSession?.session_id ?? sessionId,
          backendTranscriptSessionId: transcript?.session_id ?? backendSession?.session_id ?? sessionId,
          backendTranscriptId: transcript?.transcript_id,
          backendTranscriptVersion: transcript?.version,
          backendReportId: backendReport?.report_id ?? reportId ?? backendSession?.report_id,
          backendReportVersion: backendReport?.version,
          reportGeneratedFromVersions: backendReport?.generated_from_versions,
          reportId: backendReport?.report_id ?? reportId ?? backendSession?.report_id,
          featureSetId: backendFeatures?.feature_set_id ?? backendSession?.feature_set_id,
          featureTranscriptVersion: backendFeatures?.transcript_version,
          transcriptText: transcript?.raw_text ?? "",
          transcriptLines: lines,
          chatMetadata: parsed?.metadata ?? emptyState.chatMetadata,
          chatWarnings: parsed?.warnings ?? [],
          chatValidationIssues: parsed?.validationIssues ?? [],
          transcriptReady: Boolean(transcript),
          transcriptAttested: Boolean(transcript?.therapist_attested),
          transcriptDraftLabel: transcript?.source?.includes("asr_draft")
            ? DRAFT_ASR_TRANSCRIPT_LABEL
            : undefined,
          transcriptReviewStatus: transcript?.therapist_attested ? "reviewed" : transcript ? "in_review" : "not_started",
          qaStatus: normalizeBackendQaStatus(transcript?.qa_status),
          qaIssues: (transcript?.qa_issues ?? []).map((issue) => typeof issue === "string" ? issue : issue.message ?? "Transcript QA issue"),
          transcriptSaveStatus: transcript ? "saved" : "idle",
          ...(analysisSummary ?? {}),
          analysisStatus: findingsAreStale ? "stale" : backendFeatures ? "completed" : "not_started",
          featuresExtracted: Boolean(backendSession?.feature_set_id) && !findingsAreStale,
          featureSignals,
          mlReadiness,
          mlDecisionSupport,
          aiReview,
          reportStatus: normalizeHydratedReportStatus(backendReport?.status),
          workflowLoading: false,
          statusMessage: transcript ? "Persisted transcript loaded." : "Persisted session loaded.",
          error: undefined
        });
        setAudioUrl(resolvedAudioUrl);
        setState(sessionWorkflowReducer(loadingState, { type: "hydration-succeeded", state: hydrated }));
        setDraftTranscript(hydrated.transcriptText);
        setEditorLines(hydrated.transcriptLines);
        setIsHydrated(true);
        if (unfinishedJob && backendSession && UNFINISHED_JOB_STATUSES.has(unfinishedJob.status)) {
          resumeTranscriptionRef.current(unfinishedJob.jobId, backendSession.session_id);
        }
      } catch (error) {
        if (cancelled) return;
        const failure = classifyWorkflowLoadFailure(error, "workflow");
        setBackendUnavailable(failure.backendUnavailable);
        const failedState = saveWorkflowState(sessionWorkflowReducer(
          createIdentityScopedWorkflowState(),
          { type: "request-failed", message: failure.statusMessage, error: failure.error },
        ));
        setAudioUrl(undefined);
        setState(failedState);
        setDraftTranscript("");
        setEditorLines([]);
        setSourceFilename(undefined);
        setIsHydrated(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [caseId, hasLocator, mode, reportId, sessionId, setBackendUnavailable, transcriptId]);

  useEffect(() => {
    return () => {
      if (audioUrl?.startsWith("blob:")) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  useEffect(() => {
    if (state.transcriptSaveStatus !== "unsaved" && state.transcriptSaveStatus !== "failed") return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [state.transcriptSaveStatus]);

  const activeMode = mode ?? (state.source === "paste-transcript" ? "paste" : state.source === "cha-upload" ? "cha" : state.source === "audio-upload" ? "audio" : undefined);

  function persist(next: WorkflowState) {
    const saved = saveWorkflowState(next);
    workflowStateRef.current = saved;
    setState(saved);
    return saved;
  }

  function currentWorkflowRequestIdentity() {
    const current = workflowStateRef.current;
    return {
      revision: workflowRevisionRef.current,
      sessionId: current.backendTranscriptSessionId ?? current.backendSessionId,
      transcriptId: current.backendTranscriptId,
      transcriptVersion: current.backendTranscriptVersion,
    };
  }

  function handleRecordingMetadata(metadata: RecordingMetadata) {
    setState((current) => {
      const startingNewRecording = metadata.recordingStatus === "recording"
        && current.recordingStatus !== "recording"
        && current.recordingStatus !== "paused";
      return saveWorkflowState(ensureWorkflowSession(current, "recording", {
        recordingStatus: metadata.recordingStatus,
        recordingSeconds: metadata.durationSeconds,
        audioMimeType: metadata.mimeType,
        recordingCreatedAt: metadata.createdAt,
        hasUnsavedRecording: metadata.hasUnsavedRecording,
        recordingClearedForPrivacy: false,
        mockAudioStored: false,
        transcriptionJobId: startingNewRecording ? undefined : current.transcriptionJobId,
        transcriptionJobStatus: startingNewRecording ? undefined : current.transcriptionJobStatus,
        transcriptionJobMessage: startingNewRecording ? undefined : current.transcriptionJobMessage,
        transcriptDraftLabel: startingNewRecording ? undefined : current.transcriptDraftLabel,
        transcriptText: startingNewRecording ? "" : current.transcriptText,
        transcriptLines: startingNewRecording ? [] : current.transcriptLines,
        transcriptReady: false,
        transcriptReviewStatus: "not_started",
        qaStatus: "not_run",
        qaIssues: [],
        analysisStatus: "not_started",
        reportStatus: "not_started",
        statusMessage: metadata.hasUnsavedRecording
          ? "Recording is available for playback on this page only. It has not been uploaded or transcribed."
          : metadata.recordingStatus === "recording"
            ? "Microphone recording started. Audio remains in memory only."
            : metadata.recordingStatus === "paused"
              ? "Recording paused. Audio remains in memory only."
              : metadata.recordingStatus === "idle"
                ? "In-memory recording cleared."
                : "Transcription is experimental; upload the recording to request a draft.",
        error: metadata.error
      }));
    });
  }

  async function handleUploadForTranscription() {
    if (!recordedAudio || !state.sessionId) return;
    setUploadStep("uploading");
    setBusy(true);
    try {
      const provider = await findAvailableTranscriptionProvider();
      if (!provider) {
        setTransJobStatus("unavailable");
        setTransJobMessage(
          "Speech recognition is not enabled on this server, so the recording was not uploaded. Paste or import the transcript instead."
        );
        setUploadStep("error");
        setBusy(false);
        return;
      }
      const { audioFileId } = await uploadAudioBlobToBackend(
        state.sessionId, recordedAudio.blob,
        { durationSeconds: recordedAudio.metadata.durationSeconds,
          mimeType: recordedAudio.metadata.mimeType ?? "audio/webm",
          extension: recordedAudio.extension }
      );
      const { jobId } = await startBackendTranscriptionJob(state.sessionId, audioFileId, provider);
      setTransJobId(jobId);
      setUploadStep("polling");
      setTransJobStatus("queued");
      setTransJobMessage("Audio processing queued...");
      void pollUntilComplete(jobId, transcriptionWaitBudgetMs(recordedAudio.metadata.durationSeconds));
    } catch (err) {
      setTransJobMessage(err instanceof Error ? err.message : "Upload failed.");
      setTransJobStatus("failed");
      setUploadStep("error");
      setBusy(false);
    }
  }

  async function pollUntilComplete(jobId: string, waitBudgetMs: number, targetSessionId = state.sessionId) {
    const interval = typeof process !== "undefined" && process.env.NODE_ENV === "test" ? 10 : 2000;
    const maxAttempts = Math.ceil(waitBudgetMs / 2000);
    let attempts = 0;
    while (attempts < maxAttempts) {
      await new Promise(r => setTimeout(r, interval));
      try {
        const poll = await pollTranscriptionJob(jobId);
        setTransJobStatus(poll.status);
        setTransJobMessage(poll.message);
        if (poll.status === "needs_review" || poll.status === "completed") {
          setUploadStep("done");
          if (poll.transcriptId) {
            try {
              const transcript = await getBackendSessionTranscript(targetSessionId!);
              const lines = backendTranscriptLines(transcript);
              setState(prev => {
                const next: WorkflowState = {
                  ...prev,
                  backendTranscriptId: poll.transcriptId,
                  backendTranscriptVersion: transcript.version,
                  backendTranscriptSessionId: prev.backendSessionId ?? prev.sessionId,
                  transcriptText: transcript.raw_text ?? "",
                  transcriptLines: lines,
                  transcriptReady: true,
                  // The draft was written by the backend, so there is nothing unsaved.
                  transcriptSaveStatus: "saved",
                  transcriptionJobId: jobId,
                  transcriptionJobStatus: "completed",
                  transcriptionJobMessage: poll.message,
                  transcriptReviewStatus: "in_review",
                  transcriptDraftLabel: (transcript.source?.includes("asr_draft") || poll.status === "needs_review" || poll.status === "completed")
                    ? DRAFT_ASR_TRANSCRIPT_LABEL
                    : undefined,
                  statusMessage: "Transcript ready for review.",
                  error: undefined
                };
                saveWorkflowState(next);
                return next;
              });
              setEditorLines(lines);
              setDraftTranscript(transcript.raw_text ?? "");
            } catch (err) {
              console.error("Failed to load transcript after job completion", err);
            }
          }
          setBusy(false);
          return;
        }
        if (poll.status === "failed" || poll.status === "cancelled") {
          setUploadStep("error");
          setBusy(false);
          return;
        }
      } catch { /* network error, keep polling */ }
      attempts++;
    }
    setTransJobStatus("failed");
    setTransJobMessage("Transcription is taking longer than expected. Try again or use manual paste.");
    setUploadStep("error");
    setBusy(false);
  }

  async function handleTranscriptSubmit(
    source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">,
    reviewed = false,
    /** Text and file name handed over directly, when they are not yet in state. */
    provided?: { text: string; filename?: string },
  ) {
    const sourceText = provided?.text ?? draftTranscript;
    const submittedFilename = provided ? provided.filename : sourceFilename;
    let intake;
    try {
      intake = prepareTranscriptIntake(source, sourceText);
      setIntakeError("");
    } catch (error) {
      setIntakeError(error instanceof Error ? error.message : "Transcript could not be read.");
      return;
    }
    setBusy(true);
    const localSession = persist(ensureWorkflowSession(state, source, {
      sourceFilename: source === "cha-upload" ? submittedFilename : undefined,
      transcriptText: intake.transcriptText,
      transcriptLines: intake.transcriptLines,
      chatMetadata: intake.metadata,
      chatWarnings: intake.warnings,
      chatValidationIssues: intake.validationIssues,
      transcriptReady: true,
      transcriptReviewStatus: reviewed ? "in_review" : "draft",
      transcriptAttested: false,
      qaStatus: "not_run",
      qaIssues: [],
      analysisStatus: "not_started",
      reportStatus: "not_started",
      statusMessage: reviewed ? "Saving therapist transcript review..." : "Saving transcript source material...",
      error: undefined
    }));
    try {
      let backendSessionId = localSession.backendSessionId;
      let backendCaseId = localSession.caseId;
      if (!backendSessionId) {
        const backendSession = await createBackendSession(source);
        backendSessionId = backendSession.session_id;
        backendCaseId = backendSession.case_id;
      }
      const reviewerNote = reviewed
        ? "Therapist reviewed the transcript in the simplified workflow."
        : source === "cha-upload"
          ? "CHA transcript added to the simplified workflow."
          : "Pasted transcript added to the simplified workflow.";
      const updated = await sessionWorkflowService.saveTranscript({
        sessionId: backendSessionId,
        transcriptId: localSession.backendTranscriptId,
        source,
        originalText: sourceText,
        normalizedText: intake.transcriptText,
        sourceFilename: submittedFilename,
      });
      if (view === "chat") {
        // The conversation stays open, so take the saved lines and version
        // from the response instead of from a reload.
        const savedLines = backendTranscriptLines(updated);
        const lines = savedLines.length ? savedLines : intake.transcriptLines;
        setEditorLines(lines);
        setDraftTranscript(intake.transcriptText);
        persist({
          ...localSession,
          backendSessionId,
          backendTranscriptId: updated.transcript_id,
          backendTranscriptVersion: updated.version,
          backendTranscriptSessionId: backendSessionId,
          caseId: backendCaseId,
          caseInfo: { ...localSession.caseInfo, caseId: backendCaseId },
          transcriptText: intake.transcriptText,
          transcriptLines: lines,
          transcriptReady: true,
          transcriptCompleteness: 0,
          transcriptAttested: Boolean(updated.therapist_attested),
          transcriptReviewStatus: updated.therapist_attested ? "reviewed" : "in_review",
          transcriptSaveStatus: "saved",
          statusMessage: "Transcript saved and ready for therapist review.",
          error: undefined,
        });
        return;
      }
      const savedState = persist({
        ...localSession,
        backendSessionId,
        backendTranscriptId: updated.transcript_id,
        backendTranscriptSessionId: backendSessionId,
        caseId: backendCaseId,
        caseInfo: {
          ...localSession.caseInfo,
          caseId: backendCaseId
        },
        transcriptText: intake.transcriptText,
        transcriptLines: intake.transcriptLines,
        chatMetadata: intake.metadata,
        chatWarnings: intake.warnings,
        chatValidationIssues: intake.validationIssues,
        transcriptReady: true,
        transcriptCompleteness: 0,
        transcriptAttested: Boolean(updated.therapist_attested),
        transcriptReviewStatus: updated.therapist_attested ? "reviewed" : "draft",
        transcriptSaveStatus: "saved",
        statusMessage: "Transcript saved and ready for therapist review.",
        error: undefined
      });
      router.push(workflowSessionHref("transcript", savedState));
      return;
    } catch {
      setBackendUnavailable(true);
      persist({
        ...localSession,
        transcriptText: intake.transcriptText,
        transcriptLines: intake.transcriptLines,
        chatMetadata: intake.metadata,
        chatWarnings: intake.warnings,
        chatValidationIssues: intake.validationIssues,
        transcriptReady: false,
        transcriptAttested: false,
        transcriptReviewStatus: "draft",
        transcriptSaveStatus: "failed",
        transcriptCompleteness: 0,
        statusMessage: "Failed to save transcript.",
        error: "Backend unavailable. Transcript input remains available for retry and was not persisted."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyze() {
    if (openGates && state.transcriptSaveStatus !== "saved") {
      persist({ ...state, statusMessage: "Unsaved transcript edits.", error: "Save transcript edits before running QA." });
      return;
    }
    if (!openGates && !isTranscriptUnlocked(state)) {
      persist({
        ...state,
        statusMessage: `${FEATURE_EXTRACTION_NOUN} is locked until the transcript is reviewed and attested.`,
        error: "Review the transcript, run QA, and attest it before extracting features."
      });
      return;
    }
    setBusy(true);
    const analyzingState = persist(sessionWorkflowReducer(
      ensureWorkflowSession(state, state.source ?? "recording"),
      { type: "findings-started" },
    ));
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: analyzingState.backendTranscriptSessionId ?? analyzingState.backendSessionId,
      transcriptId: analyzingState.backendTranscriptId,
      transcriptVersion: analyzingState.backendTranscriptVersion,
    };
    try {
      const targetSession = analyzingState.backendTranscriptSessionId ?? analyzingState.backendSessionId;
      if (!targetSession || !analyzingState.backendTranscriptId) throw new Error("Persistent transcript unavailable.");
      const backendAnalysis = await sessionWorkflowService.extractFindings(targetSession, analyzingState.backendTranscriptId);
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      // Readiness was last checked before features existed; refresh it so the
      // findings page does not show a stale "features not extracted" block.
      const mlReadiness = await getMlReadiness(analyzingState.backendTranscriptId).catch(() => undefined);
      // The conversation shows the measures without a reload, so it reads the
      // values the backend just stored instead of waiting for the next visit.
      // The other views navigate to Findings, which loads them itself.
      let featureSignals: WorkflowState["featureSignals"] | undefined;
      if (view === "chat") {
        featureSignals = buildFeatureSignals(
          await getBackendSessionFeatures(targetSession).catch(() => undefined),
          await getBackendFeatureDefinitions().catch(() => []),
        );
        if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      }
      persist({
        ...sessionWorkflowReducer(analyzingState, { type: "findings-succeeded", findings: backendAnalysis }),
        mlReadiness,
        ...(featureSignals ? { featureSignals } : {}),
        // With open gates the server records the attestation when analysis starts.
        ...(openGates ? { transcriptAttested: true, transcriptReviewStatus: "reviewed" as const } : {}),
      });
      if (view !== "chat") router.push(workflowSessionHref("findings", analyzingState));
    } catch {
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist(sessionWorkflowReducer(analyzingState, { type: "findings-failed", error: "Backend unavailable. No feature result was recorded." }));
    } finally {
      if (canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
    }
  }

  async function handleGenerateReport() {
    if (!openGates && !isTranscriptUnlocked(state)) {
      persist({
        ...state,
        statusMessage: "Report generation is locked until the transcript is reviewed and attested.",
        error: "Review the transcript, run QA, and attest it before generating a report."
      });
      return;
    }
    if (!state.featuresExtracted) {
      persist({
        ...state,
        statusMessage: "Report generation is locked until language-sample features are extracted.",
        error: "Extract language-sample features from the attested transcript before generating a report."
      });
      return;
    }
    setBusy(true);
    const reportingState = persist(sessionWorkflowReducer(
      ensureWorkflowSession(state, state.source ?? "recording"),
      { type: "report-started" },
    ));
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: reportingState.backendTranscriptSessionId ?? reportingState.backendSessionId,
      transcriptId: reportingState.backendTranscriptId,
      transcriptVersion: reportingState.backendTranscriptVersion,
    };
    try {
      const targetSession = reportingState.backendTranscriptSessionId ?? reportingState.backendSessionId;
      if (!targetSession) throw new Error("Persistent session unavailable.");
      const report = await sessionWorkflowService.generateReport({ sessionId: targetSession });
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      if (!report.report_id) throw new Error("Report ID missing.");
      const savedState = persist(sessionWorkflowReducer(reportingState, {
        type: "report-succeeded",
        reportId: report.report_id,
        markdown: report.content_markdown ?? report.markdown ?? "",
        finalized: report.status === "Signed Off",
        version: report.version,
        generatedFromVersions: report.generated_from_versions,
      }));
      router.push(resolveSessionHref("report", savedState.backendSessionId ?? savedState.backendTranscriptSessionId, {
        caseId: savedState.caseId,
        transcriptId: savedState.backendTranscriptId,
        reportId: report.report_id,
      }));
    } catch {
      if (!canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist(sessionWorkflowReducer(reportingState, { type: "report-failed", error: "Backend unavailable. No report draft was created." }));
    } finally {
      if (canSettleWorkflowRequest(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
    }
  }

  async function handleGenerateAiReview() {
    if (!state.featuresExtracted) {
      persist({
        ...state,
        statusMessage: "AI-assisted review requires extracted features from a reviewed transcript.",
        error: "Extract transcript features before generating AI-assisted review support."
      });
      return;
    }
    setBusy(true);
    const aiState = state;
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: aiState.backendTranscriptSessionId ?? aiState.backendSessionId,
      transcriptId: aiState.backendTranscriptId,
      transcriptVersion: aiState.backendTranscriptVersion,
    };
    try {
      const resolvedSessionId = aiState.backendSessionId ?? aiState.backendTranscriptSessionId;
      if (!resolvedSessionId) throw new Error("Persistent session unavailable.");
      const aiReview = await generateAiReview(resolvedSessionId);
      if (!canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      persist({
        ...aiState,
        aiReview,
        statusMessage: `AI-assisted review generated. ${THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE}.`,
        error: undefined
      });
    } catch {
      if (!canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist({
        ...aiState,
        aiReview: undefined,
        statusMessage: "AI-assisted review unavailable — backend verification required.",
        error: "Backend unavailable. No AI-assisted review was generated or loaded."
      });
    } finally {
      if (canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
    }
  }

  async function handleGenerateMlDecisionSupport() {
    if (!state.featuresExtracted) {
      persist({
        ...state,
        statusMessage: "Evidence review requires extracted features from a reviewed transcript.",
        error: "Extract transcript features before generating model-informed review cues."
      });
      return;
    }
    setBusy(true);
    const mlState = state;
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: mlState.backendTranscriptSessionId ?? mlState.backendSessionId,
      transcriptId: mlState.backendTranscriptId,
      transcriptVersion: mlState.backendTranscriptVersion,
    };
    try {
      if (!mlState.backendTranscriptId) throw new Error("Persistent transcript unavailable.");
      const mlDecisionSupport = await generateMlDecisionSupport(
        mlState.backendTranscriptId,
        mlState.mlReadiness?.providerId,
      );
      if (!canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      persist({
        ...mlState,
        mlDecisionSupport,
        statusMessage: `Evidence review generated. ${THERAPIST_INTERPRETATION_IS_REQUIRED_CLAUSE}.`,
        error: undefined
      });
    } catch {
      if (!canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist({
        ...mlState,
        mlDecisionSupport: undefined,
        statusMessage: "ML review unavailable — backend verification required.",
        error: "Backend unavailable. No ML review result was generated or loaded."
      });
    } finally {
      if (canApplyMlDecisionSupportSettlement(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
    }
  }

  async function handleApproveReviewedCues() {
    const resolvedSessionId = state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId;
    if (!resolvedSessionId || busy) return;
    setBusy(true);
    try {
      const acknowledgement = await acknowledgeSessionCues(resolvedSessionId);
      persist({
        ...state,
        cuesAcknowledgedAt: acknowledgement.acknowledgedAt,
        cuesAcknowledgedBy: acknowledgement.acknowledgedBy,
        statusMessage: "Reviewed cues acknowledged and recorded server-side.",
        error: undefined,
      });
    } catch {
      persist({
        ...state,
        statusMessage: "Reviewed cues acknowledgement was not recorded.",
        error: undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleProfileEvidenceReview(
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote = ""
  ) {
    if (!state.mlDecisionSupport) return;
    setBusy(true);
    try {
      const mlDecisionSupport = await updateProfileEvidenceReview(
        state.mlDecisionSupport.resultId,
        profileCode,
        status,
        therapistNote
      );
      persist({
        ...state,
        mlDecisionSupport,
        statusMessage: status === "reviewed"
          ? `${profileCode} evidence marked reviewed. This records reading, not endorsement.`
          : `${profileCode} clinical disagreement recorded without deleting provider output.`,
        error: undefined
      });
    } catch {
      persist({
        ...state,
        statusMessage: "Evidence review state was not saved.",
        error: "Backend unavailable. The evidence disposition was not changed."
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleCueReview(cueCode: string, status: "acknowledged" | "dismissed") {
    if (!state.mlDecisionSupport) return;
    setBusy(true);
    try {
      const mlDecisionSupport = await updateCueReview(state.mlDecisionSupport.resultId, cueCode, status);
      persist({
        ...state,
        mlDecisionSupport,
        statusMessage: status === "acknowledged"
          ? "Cue confirmed after checking the transcript."
          : "Cue dismissed; the provider output is kept for audit.",
        error: undefined
      });
    } catch {
      persist({
        ...state,
        statusMessage: "Cue review was not saved.",
        error: "Backend unavailable. The cue was not changed."
      });
    } finally {
      setBusy(false);
    }
  }

  const sessionContext: SessionContext = {
    sessionId: state.backendSessionId ?? state.sessionId ?? sessionId,
    caseId: state.caseId || caseId,
    caseLabel: state.childName || state.caseInfo.clientLabel || state.caseId || caseId,
    sourceLabel: workflowSourceLabel(state.source),
    consentStatus: caseConsent,
    workflowStatus: pipelineStatusValue.replaceAll("_", " "),
    dataMode: state.backendSessionId
      ? "backend"
      : backendUnavailable && hasLocator
        ? "unavailable"
        : "local_draft",
    activeView: view === "chat" ? "intake" : view,
    completion: sessionCompletion(state, openGates),
  };

  if (view === "chat") {
    const resolvedSessionId = state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId ?? sessionId;
    const identity = { caseId: state.caseId || caseId, transcriptId: state.backendTranscriptId };
    return {
      view: "chat",
      backendUnavailable,
      viewProps: {
        sessionContext,
        state,
        hydrated: isHydrated,
        busy,
        backendUnavailable,
        source: activeMode === "audio" ? "audio" : "recording",
        lines: editorLines,
        audioUrl,
        notes: sessionNotes,
        summary: sessionSummary,
        attachError: intakeError,
        audio: {
          recorded: recordedAudio
            ? { blob: recordedAudio.blob, durationSeconds: recordedAudio.metadata.durationSeconds }
            : null,
          step: uploadStep,
          jobStatus: transJobStatus,
          jobMessage: transJobMessage,
          fileError: audioFileError,
        },
        hrefs: {
          transcript: resolveSessionHref("transcript", resolvedSessionId, identity),
          findings: resolveSessionHref("findings", resolvedSessionId, identity),
          report: resolveSessionHref("report", resolvedSessionId, {
            ...identity,
            reportId: state.backendReportId ?? state.reportId,
          }),
        },
        onRecordingMetadata: handleRecordingMetadata,
        onRecordingReady: handleRecordingReady,
        onAudioFile: handleAudioFile,
        onDiscardAudio: () => {
          setRecordedAudio(null);
          setAudioFileError(undefined);
          setUploadStep("idle");
        },
        onUploadAudio: handleUploadForTranscription,
        onAttachTranscript: handleAttachTranscript,
        onAssignUnknownSpeakers: (speaker) => handleSaveTranscriptDraft(assignUnknownSpeakers(editorLines, speaker)),
        onRetrySave: () => handleSaveTranscriptDraft(editorLines),
        onExtractMeasures: handleAnalyze,
        onGenerateReport: handleGenerateReport,
        onSaveNote: handleSaveNote,
      },
    };
  }

  if (view === "findings") {
    return {
      view: "findings",
      backendUnavailable,
      viewProps: {
        sessionContext,
        state,
        busy,
        onRegenerateFindings: handleAnalyze,
        onGenerateReport: handleGenerateReport,
        onGenerateMlDecisionSupport: handleGenerateMlDecisionSupport,
        onGenerateAiReview: handleGenerateAiReview,
        onProfileEvidenceReview: handleProfileEvidenceReview,
        onCueReview: handleCueReview,
        onApproveReviewedCues: handleApproveReviewedCues,
        backendUnavailable,
      },
    };
  }

  return {
    view: "transcript",
    backendUnavailable,
    viewProps: {
      sessionContext,
      state,
      lines: editorLines,
      busy,
      backendUnavailable,
      audioUrl,
      onLinesChange: (lines) => {
        workflowRevisionRef.current += 1;
        activeTranscriptSaveRevisionRef.current = null;
        setBusy(false);
        setEditorLines(lines);
        persist({
          ...sessionWorkflowReducer(state, { type: "transcript-edited", lines }),
          statusMessage: "Unsaved transcript edits.",
        });
      },
      onSaveDraft: () => handleSaveTranscriptDraft(editorLines),
      onRunQa: () => handleRunTranscriptQa(editorLines),
      onAttest: handleAttestTranscript,
      onExtractFeatures: handleAnalyze,
      onGenerateReport: handleGenerateReport,
      onExport: handleExportCha,
    },
  };

  /** An existing audio file takes the same path as a recording made here. */
  async function handleAudioFile(file: File) {
    const described = describeAudioFile(file);
    if (!described) {
      setAudioFileError("unsupported");
      return;
    }
    setAudioFileError(undefined);
    const durationSeconds = await readAudioDurationSeconds(file);
    setRecordedAudio({
      blob: file,
      extension: described.extension,
      metadata: {
        recordingStatus: "stopped",
        durationSeconds,
        mimeType: described.mimeType,
        hasUnsavedRecording: false,
      },
    });
    setUploadStep("confirm");
  }

  async function handleAttachTranscript(file: File) {
    if (!file.name.toLowerCase().endsWith(".cha")) {
      setIntakeError("Only .cha transcript files can be attached.");
      return;
    }
    setSourceFilename(file.name);
    await handleTranscriptSubmit("cha-upload", false, { text: await file.text(), filename: file.name });
  }

  /** Adds one line to the session's notes. Resolves to whether it was saved. */
  async function handleSaveNote(text: string): Promise<boolean> {
    const targetSession = state.backendSessionId ?? state.sessionId;
    const note = text.trim();
    if (!targetSession || !note) return false;
    const next = sessionNotes.trim() ? `${sessionNotes.trim()}\n${note}` : note;
    try {
      const updated = await updateBackendSessionNotes(targetSession, next);
      setSessionNotes(updated.notes ?? next);
      return true;
    } catch {
      setBackendUnavailable(true);
      return false;
    }
  }

  async function handleSaveTranscriptDraft(lines: TranscriptLine[]) {
    if (activeTranscriptSaveRevisionRef.current !== null) return;
    setBusy(true);
    const transcriptText = buildBasicChatExport({
      lines,
      metadata: state.chatMetadata,
      includeMedia: state.mockAudioStored || Boolean(state.chatMetadata.media),
      fallbackMediaName: `${state.sessionId ?? "local-session"}_audio`,
      allowInvalid: true
    }).trimEnd();
    const edited = sessionWorkflowReducer(state, { type: "transcript-edited", lines });
    const next = persist(sessionWorkflowReducer(
      ensureWorkflowSession(edited, state.source ?? "paste-transcript"),
      { type: "transcript-save-started", transcriptText },
    ));
    const requestIdentity = {
      revision: ++workflowRevisionRef.current,
      sessionId: next.backendTranscriptSessionId ?? next.backendSessionId,
      transcriptId: next.backendTranscriptId,
      transcriptVersion: next.backendTranscriptVersion,
    };
    activeTranscriptSaveRevisionRef.current = requestIdentity.revision;
    setDraftTranscript(transcriptText);
    try {
      if (!next.backendTranscriptId) throw new Error("No persistent transcript exists.");
      const updated = await sessionWorkflowService.saveTranscript({
        sessionId: next.backendTranscriptSessionId ?? next.backendSessionId ?? "",
        transcriptId: next.backendTranscriptId,
        source: next.source === "cha-upload" ? "cha-upload" : "paste-transcript",
        originalText: transcriptText,
        normalizedText: transcriptText,
        sourceFilename: next.sourceFilename,
      });
      if (!canApplyTranscriptSaveSettlement(requestIdentity, currentWorkflowRequestIdentity(), "fulfilled")) return;
      setBusy(false);
      const savedLines = backendTranscriptLines(updated);
      setEditorLines(savedLines.length ? savedLines : lines);
      persist(sessionWorkflowReducer(next, {
        type: "transcript-save-succeeded",
        lines: savedLines.length ? savedLines : lines,
        backendTranscriptVersion: updated.version,
      }));
    } catch {
      if (!canApplyTranscriptSaveSettlement(requestIdentity, currentWorkflowRequestIdentity(), "rejected")) return;
      setBackendUnavailable(true);
      persist(sessionWorkflowReducer(next, { type: "transcript-save-failed", error: "Backend unavailable. Edits remain unsaved and can be retried." }));
    } finally {
      if (activeTranscriptSaveRevisionRef.current === requestIdentity.revision) {
        activeTranscriptSaveRevisionRef.current = null;
      }
      if (canApplyTranscriptSaveSettlement(requestIdentity, currentWorkflowRequestIdentity(), "finalized")) {
        setBusy(false);
      }
    }
  }

  async function handleRunTranscriptQa(lines: TranscriptLine[]) {
    if (!state.backendTranscriptId || state.transcriptSaveStatus !== "saved") {
      persist({ ...state, statusMessage: "Save transcript edits before running QA.", error: "Transcript QA requires a backend-saved draft." });
      return;
    }
    const localQa = evaluateTranscriptQa(lines, state.chatMetadata);
    setBusy(true);
    const transcriptText = buildBasicChatExport({
      lines,
      metadata: state.chatMetadata,
      includeMedia: state.mockAudioStored || Boolean(state.chatMetadata.media),
      fallbackMediaName: `${state.sessionId ?? "local-session"}_audio`,
      allowInvalid: true
    }).trimEnd();
    let next = persist({
      ...state,
      transcriptText,
      transcriptLines: lines,
      transcriptReady: lines.length > 0,
      transcriptAttested: false,
      transcriptReviewStatus: "in_review",
      qaStatus: localQa.status,
      qaIssues: localQa.issues,
      qaSummary: localQa.summary,
      statusMessage: "QA running...",
      error: undefined
    });
    const targetTranscriptId = next.backendTranscriptId;
    if (targetTranscriptId) {
      try {
        const backendQa = await sessionWorkflowService.runQa(targetTranscriptId);
        next = persist(sessionWorkflowReducer(next, {
          type: "qa-succeeded",
          status: (backendQa.status ?? backendQa.qa_status ?? next.qaStatus) as any,
          issues: backendQa.issues ?? next.qaIssues,
          summary: backendQa.summary ?? localQa.summary,
        }));
      } catch {
        setBackendUnavailable(true);
        persist(sessionWorkflowReducer(next, { type: "qa-failed", error: "Backend QA was unavailable. Retry when the backend is available." }));
      }
    } else {
      persist(sessionWorkflowReducer(next, { type: "qa-failed", error: "No persistent transcript ID is available." }));
    }
    setBusy(false);
  }

  async function handleAttestTranscript() {
    if (state.qaStatus === "not_run" || state.qaStatus === "fail" || !state.backendTranscriptId || state.transcriptSaveStatus !== "saved") return;
    setBusy(true);
    persist({ ...state, statusMessage: "Recording transcript attestation...", error: undefined });
    try {
      await sessionWorkflowService.attest(state.backendTranscriptId);
      persist(sessionWorkflowReducer(state, { type: "attestation-succeeded" }));
    } catch (error) {
      if (!(error instanceof ApiError) || error.status >= 500) {
        setBackendUnavailable(true);
      }
      persist(sessionWorkflowReducer(state, { type: "attestation-failed", error: getAttestationFailureCopy(error) }));
    }
    setBusy(false);
  }

  function handleExportCha() {
    if (!state.backendTranscriptId) return;
    void exportReviewedCha(state.backendTranscriptId).then((result) => {
      downloadText(result.cha_text, result.filename, "text/x-chat");
    }).catch(() => persist({ ...state, statusMessage: "Export failed.", error: "Backend unavailable. The transcript was not exported." }));
  }
}

function workflowSourceLabel(source?: WorkflowSource): string | undefined {
  if (source === "audio-upload") return "Uploaded audio (experimental)";
  if (source === "cha-upload") return ".cha transcript";
  if (source === "paste-transcript") return "Pasted transcript";
  if (source === "recording") return "Browser recording";
  return undefined;
}

function normalizeBackendQaStatus(status?: string): WorkflowState["qaStatus"] {
  const normalized = status?.toLowerCase();
  if (normalized === "pass") return "pass";
  if (normalized === "warning") return "warning";
  if (normalized === "fail") return "fail";
  return "not_run";
}

function workflowSessionHref(view: "intake" | "transcript" | "findings" | "report", state: WorkflowState, reportId?: string) {
  return resolveSessionHref(view, state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId, {
    caseId: state.caseId,
    transcriptId: state.backendTranscriptId,
    reportId: reportId ?? state.backendReportId ?? state.reportId,
  });
}

// A job found after a reload has no known length to estimate from, so it gets the longest wait.
const RESUMED_TRANSCRIPTION_WAIT_MS = 20 * 60_000;
const UNFINISHED_JOB_STATUSES: ReadonlySet<string> = new Set(["queued", "processing", "transcription_completed"]);

// Extension to the content type the upload endpoint accepts for it.
const AUDIO_FILE_TYPES: Record<string, string> = {
  wav: "audio/wav",
  mp3: "audio/mpeg",
  m4a: "audio/mp4",
  mp4: "audio/mp4",
  webm: "audio/webm",
  ogg: "audio/ogg",
  mov: "video/quicktime",
};

/** The type and extension to upload an audio file under, or null when it is not a supported format. */
function describeAudioFile(file: File): { mimeType: string; extension: string } | null {
  const extension = file.name.includes(".") ? file.name.split(".").pop()!.toLowerCase() : "";
  const mimeType = AUDIO_FILE_TYPES[extension];
  return mimeType ? { mimeType, extension } : null;
}

/** Length of an audio file in whole seconds; 0 when the browser cannot read it. */
function readAudioDurationSeconds(file: Blob): Promise<number> {
  if (typeof document === "undefined" || typeof URL.createObjectURL !== "function") return Promise.resolve(0);
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const audio = document.createElement("audio");
    const settle = (seconds: number) => {
      URL.revokeObjectURL(url);
      resolve(Number.isFinite(seconds) && seconds > 0 ? Math.round(seconds) : 0);
    };
    const timer = window.setTimeout(() => settle(0), 4000);
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      window.clearTimeout(timer);
      settle(audio.duration);
    };
    audio.onerror = () => {
      window.clearTimeout(timer);
      settle(0);
    };
    audio.src = url;
  });
}

function downloadText(text: string, filename: string, contentType: string) {
  if (typeof document === "undefined" || typeof URL.createObjectURL !== "function") return;
  const url = URL.createObjectURL(new Blob([text], { type: `${contentType};charset=utf-8` }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

async function createBackendAudioObjectUrl(audioFileId: string): Promise<string> {
  const blob = await apiBlob(`/audio/${audioFileId}/file`);
  return URL.createObjectURL(blob);
}

function estimateTranscriptCompleteness(lines: TranscriptLine[]) {
  if (lines.length === 0) return 0;
  const populated = lines.filter((line) => line.text.trim().length > 0).length / lines.length;
  const speakers = lines.filter((line) => line.speaker && line.speaker !== "UNK").length / lines.length;
  const timings = lines.filter((line) => line.startMs !== undefined && line.endMs !== undefined).length / lines.length;
  return Math.max(0, Math.min(100, Math.round((populated * 0.5 + speakers * 0.3 + timings * 0.2) * 100)));
}

function isTranscriptUnlocked(state: WorkflowState) {
  return state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
}

function normalizeHydratedReportStatus(status?: string): WorkflowState["reportStatus"] {
  const normalized = status?.trim().toLowerCase().replaceAll(" ", "_");
  if (normalized === "signed_off" || normalized === "finalized") return "finalized";
  if (normalized === "stale") return "stale";
  if (normalized === "reviewed" || normalized === "attested") return "reviewed";
  if (normalized === "draft" || normalized === "needs_review") return "draft";
  return "not_started";
}

function getAttestationFailureCopy(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your sign-in session expired before attestation was recorded. Log out, sign in again, then retry Attest transcript.";
    }
    if (error.status === 403) {
      return "This account is not allowed to attest this transcript for the active organization. Switch to the assigned therapist account or choose the correct organization, then retry.";
    }
    if (error.status === 404) {
      return "The saved transcript could not be found. Return to the session, save the transcript again, then retry attestation.";
    }
    if (error.status >= 500) {
      return "The backend could not record attestation right now. Your transcript is still saved; retry Attest transcript in a moment.";
    }
  }
  return "Attestation did not finish. Your transcript is still saved; retry Attest transcript before generating a report.";
}

function createLocalReportMarkdown(state: WorkflowState) {
  return [
    "# Draft Report Preview",
    "",
    `Child/session: ${state.childName}`,
    `Transcript status: ${state.transcriptReady ? "Ready for therapist review" : "Not ready"}`,
    `Feature summary: ${state.featureSummary.map((item) => `${item.label} ${item.value}`).join(", ") || "Pending"}`,
    "",
    "All content is decision-support only and must be edited and finalized by the therapist."
  ].join("\n");
}
