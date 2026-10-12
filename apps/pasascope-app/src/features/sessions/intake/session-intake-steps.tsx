import { ClipboardPaste, FileText, Mic, UploadCloud } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { CaregiverConsentForm } from "@/components/caregiver-consent-form";
import { AudioUploadConfirmPanel } from "@/components/audio-upload-confirm-panel";
import { BrowserAudioRecorder } from "@/components/browser-audio-recorder";
import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";
import { SafetyNotice } from "@/components/safety-notice";
import { TranscriptionJobStatusPanel, type TranscriptionJobDisplayStatus } from "@/components/transcription-job-status-panel";
import {
  Field,
  ReviewSummaryCard,
  SourceChoiceButton,
  SourceInputPanel,
  workflowSessionHref,
} from "@/features/sessions/intake/session-intake-components";
import { intakeMessages } from "@/features/sessions/intake/intake.messages";
import type { SessionIntakeViewModel } from "@/features/sessions/intake/session-intake-view";
import { useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";
import { prepareTranscriptIntake } from "@/lib/workflow";
import {
  continueToSourceMaterialBlockedReason,
  grantConsentBlockedReason,
  startTranscriptReviewBlockedReason,
} from "@/lib/workflow-gates";

const controlClass =
  "block min-h-11 w-full rounded-control border border-line-strong bg-surface px-3.5 py-2.5 text-sm text-ink outline-none transition focus-visible:border-brand focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";

export function SessionIntakeSteps({ model }: { model: SessionIntakeViewModel }) {
  const {
    intakeStep, setIntakeStep, caseConsent, intakeError, setIntakeError,
    consentChecked, setConsentChecked, consentSigner, setConsentSigner,
    consentDate, setConsentDate, consentNotes, setConsentNotes, busy,
    handleGrantConsent, sessionDetails, setSessionDetails, sessionDetailsComplete,
    transcriptSetupComplete,
    selectedSource, setSelectedSource, state, setState, recordedAudio, setRecordedAudio,
    uploadStep, setUploadStep, handleRecordingMetadata, handleRecordingReady,
    handleUploadForTranscription, transJobStatus, transJobMessage, transJobRequestedProvider,
    transJobActualProvider, backendUnavailable, draftTranscript, setDraftTranscript,
    setSourceFilename, intakeWarnings, setIntakeWarnings, intakeValidationIssues,
    setIntakeValidationIssues, handleTranscriptSubmit, transcriptLines,
    transcriptSetup, setTranscriptSetup, sourceReadyForReview, canStartTranscriptReview,
    saveSessionIntakeDraft, router,
  } = model;
  const t = useMessages(intakeMessages);
  const safety = useSafetyCopy();

  const startTranscriptReviewBlockedReasonText = canStartTranscriptReview
    ? undefined
    : startTranscriptReviewBlockedReason({
        sessionDetailsComplete,
        transcriptSetupComplete,
        sourceReadyForReview,
        selectedSource,
      });
  const continueToSourceMaterialReason = continueToSourceMaterialBlockedReason({ sessionDetailsComplete });
  const grantConsentReason = grantConsentBlockedReason({ checked: consentChecked, busy });

  return (
    <>
          {intakeStep === "details" && caseConsent !== "granted" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6" role="region" aria-label="Consent Intake Gate">
              <div>
                <h2 className="text-xl font-semibold text-ink">{t.consent.title}</h2>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {t.consent.body}
                </p>
              </div>
              {intakeError && (
                <p className="rounded-card border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-4 py-3 text-sm font-medium text-[color:var(--color-danger-text)]">
                  {intakeError}
                </p>
              )}
              <CaregiverConsentForm
                busy={busy}
                checked={consentChecked}
                onCheckedChange={setConsentChecked}
                signer={consentSigner}
                onSignerChange={setConsentSigner}
                consentDate={consentDate}
                onConsentDateChange={setConsentDate}
                notes={consentNotes}
                onNotesChange={setConsentNotes}
                onSubmit={async (event) => {
                  event.preventDefault();
                  await handleGrantConsent();
                }}
                submitLabel={t.consent.submit}
                submitBlockedReason={grantConsentReason}
                reasonId="grant-consent-reason"
                idPrefix="intake"
              />
            </WorkspacePanel>
          ) : intakeStep === "details" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">{t.steps.details}</h2>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {t.details.body}
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Field>
                  <label htmlFor="session-child-client" className="block text-sm font-semibold text-ink">{t.details.childClient}</label>
                  <input
                    id="session-child-client"
                    type="text"
                    value={sessionDetails.childClient}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, childClient: event.target.value }))}
                    className={controlClass}
                  />
                </Field>
                <Field>
                  <label htmlFor="session-clinician" className="block text-sm font-semibold text-ink">{t.details.clinician}</label>
                  <input
                    id="session-clinician"
                    type="text"
                    value={sessionDetails.clinician}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, clinician: event.target.value }))}
                    className={controlClass}
                  />
                </Field>
                <Field>
                  <label htmlFor="session-date" className="block text-sm font-semibold text-ink">{t.details.date}</label>
                  <input
                    id="session-date"
                    type="date"
                    value={sessionDetails.sessionDate}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, sessionDate: event.target.value }))}
                    className={controlClass}
                  />
                </Field>
                <Field>
                  <label htmlFor="session-time" className="block text-sm font-semibold text-ink">{t.details.time}</label>
                  <input
                    id="session-time"
                    type="time"
                    value={sessionDetails.sessionTime}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, sessionTime: event.target.value }))}
                    className={controlClass}
                  />
                </Field>
                <Field>
                  <label htmlFor="session-setting" className="block text-sm font-semibold text-ink">{t.details.setting}</label>
                  <select
                    id="session-setting"
                    value={sessionDetails.setting}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, setting: event.target.value }))}
                    className={controlClass}
                  >
                    <option value="clinic">{t.details.settings.clinic}</option>
                    <option value="home">{t.details.settings.home}</option>
                    <option value="telehealth">{t.details.settings.telehealth}</option>
                  </select>
                </Field>
                <Field>
                  <label htmlFor="session-duration" className="block text-sm font-semibold text-ink">{t.details.duration}</label>
                  <select
                    id="session-duration"
                    value={sessionDetails.durationMinutes}
                    onChange={(event) => setSessionDetails((current) => ({ ...current, durationMinutes: event.target.value }))}
                    className={controlClass}
                  >
                    <option value="30">{t.details.minutes("30")}</option>
                    <option value="45">{t.details.minutes("45")}</option>
                    <option value="60">{t.details.minutes("60")}</option>
                    <option value="90">{t.details.minutes("90")}</option>
                  </select>
                </Field>
              </div>
              <Field>
                <label htmlFor="session-goals" className="block text-sm font-semibold text-ink">{t.details.goals}</label>
                <textarea
                  id="session-goals"
                  value={sessionDetails.sessionGoals}
                  onChange={(event) => setSessionDetails((current) => ({ ...current, sessionGoals: event.target.value }))}
                  className={`${controlClass} min-h-32`}
                />
              </Field>
              <SafetyNotice>
                {safety.DECISION_SUPPORT_ONLY} {t.details.safetyNote}
              </SafetyNotice>
              <div className="flex flex-wrap justify-end gap-3">
                <ActionButton
                  type="button"
                  onClick={() => setIntakeStep("source")}
                  disabled={!sessionDetailsComplete}
                  aria-describedby={continueToSourceMaterialReason ? "continue-to-source-material-reason" : undefined}
                >
                  {t.details.continue}
                </ActionButton>
              </div>
              {continueToSourceMaterialReason ? (
                <p
                  id="continue-to-source-material-reason"
                  role="status"
                  className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]"
                >
                  {continueToSourceMaterialReason}
                </p>
              ) : null}
            </WorkspacePanel>
          ) : null}

          {intakeStep === "source" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">{t.steps.source}</h2>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {t.source.body}
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <SourceChoiceButton label={t.sourceChoices.recording} active={selectedSource === "recording"} icon={Mic} onClick={() => setSelectedSource("recording")} />
                <SourceChoiceButton label={t.sourceChoices.audio} active={selectedSource === "audio"} icon={UploadCloud} onClick={() => setSelectedSource("audio")} />
                <SourceChoiceButton label={t.sourceChoices.cha} active={selectedSource === "cha"} icon={FileText} onClick={() => setSelectedSource("cha")} />
                <SourceChoiceButton label={t.sourceChoices.paste} active={selectedSource === "paste"} icon={ClipboardPaste} onClick={() => setSelectedSource("paste")} />
              </div>

              {selectedSource === "recording" ? (
                <>
                  <WorkspacePanel className="p-5 text-center">
                    <BrowserAudioRecorder
                      initialDurationSeconds={state.recordingSeconds}
                      hadUnsavedRecording={state.recordingClearedForPrivacy}
                      onMetadataChange={handleRecordingMetadata}
                      onRecordingReady={handleRecordingReady}
                      onRecordingCleared={() => { setRecordedAudio(null); setUploadStep("idle"); }}
                    />
                  </WorkspacePanel>

                  {uploadStep === "confirm" && recordedAudio ? (
                    <AudioUploadConfirmPanel
                      blob={recordedAudio.blob}
                      durationSeconds={recordedAudio.metadata.durationSeconds}
                      onUpload={handleUploadForTranscription}
                      onCancel={() => setUploadStep("idle")}
                      backendAvailable={!backendUnavailable}
                      uploading={busy}
                    />
                  ) : null}

                  {["polling", "done", "error"].includes(uploadStep) ? (
                    <TranscriptionJobStatusPanel
                      status={transJobStatus as TranscriptionJobDisplayStatus}
                      message={transJobMessage}
                      requestedProvider={transJobRequestedProvider}
                      actualProvider={transJobActualProvider}
                      onOpenTranscript={
                        uploadStep === "done" && state.backendTranscriptId && state.sessionId
                          ? () => {
                              router.push(workflowSessionHref("transcript", state));
                            }
                          : undefined
                      }
                      onRetry={() => {
                        setUploadStep("idle");
                        setRecordedAudio(null);
                      }}
                      onUsePaste={() => {
                        setSelectedSource("paste");
                        setState((prev) => ({ ...prev, source: "paste-transcript" }));
                      }}
                    />
                  ) : null}

                  {uploadStep === "idle" && recordedAudio ? (
                    <WorkspacePanel className="p-5 text-center">
                      <p className="mb-3 text-sm text-ink-muted">{t.source.recordingCaptured}</p>
                      <PrimaryActionButton icon={UploadCloud} className="w-full" onClick={() => setUploadStep("confirm")}>
                        {t.source.uploadForTranscription}
                      </PrimaryActionButton>
                    </WorkspacePanel>
                  ) : null}
                </>
              ) : (
                <SourceInputPanel
                  mode={selectedSource === "audio" ? "audio" : selectedSource === "cha" ? "cha" : "paste"}
                  draftTranscript={draftTranscript}
                  busy={busy}
                  error={intakeError}
                  warnings={intakeWarnings}
                  validationIssues={intakeValidationIssues}
                  onDraftChange={(value) => {
                    setDraftTranscript(value);
                    setIntakeError("");
                    setIntakeWarnings([]);
                    setIntakeValidationIssues([]);
                  }}
                  onChaFile={async (file) => {
                    if (!file.name.toLowerCase().endsWith(".cha")) {
                      setSourceFilename(undefined);
                      setIntakeError(t.source.invalidExtension);
                      return;
                    }
                    const text = await file.text();
                    try {
                      const intake = prepareTranscriptIntake("cha-upload", text);
                      setSourceFilename(file.name);
                      setDraftTranscript(intake.transcriptText);
                      setIntakeError("");
                      setIntakeWarnings(intake.warnings);
                      setIntakeValidationIssues(intake.validationIssues);
                    } catch (error) {
                      setSourceFilename(undefined);
                      setDraftTranscript(text);
                      setIntakeError(error instanceof Error ? error.message : t.source.invalidFile);
                      setIntakeWarnings([]);
                      setIntakeValidationIssues([]);
                    }
                  }}
                  onTranscriptSubmit={handleTranscriptSubmit}
                />
              )}

              <WorkspacePanel className="p-5">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="font-bold text-ink">{t.source.previewTitle}</h3>
                  <span className="inline-flex items-center gap-2 rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold text-ink">
                    <span className={`h-2 w-2 rounded-full ${state.transcriptReady ? "bg-brand" : "bg-[color:var(--color-warning-border)]"}`} />
                    {state.transcriptReady ? t.view.readyForReview : t.source.previewOnly}
                  </span>
                </div>
                <div className="space-y-2 text-sm text-ink">
                  {state.transcriptReady && transcriptLines.length > 0
                    ? transcriptLines.slice(0, 6).map((line) => <p key={line}>{line}</p>)
                    : draftTranscript.trim()
                      ? draftTranscript.trim().split("\n").slice(0, 6).map((line) => <p key={line}>{line}</p>)
                      : (
                        <div className="rounded-card border border-dashed border-line bg-surface-muted p-4 text-center">
                          <p className="font-semibold text-ink">{t.source.noTranscriptTitle}</p>
                          <p className="mt-1 text-sm text-ink-muted">{t.source.noTranscriptBody}</p>
                        </div>
                      )}
                </div>
              </WorkspacePanel>

              <div className="flex flex-wrap justify-between gap-3">
                <ActionButton type="button" tone="ghost" onClick={() => setIntakeStep("details")}>
                  {t.source.back}
                </ActionButton>
                <ActionButton type="button" onClick={() => setIntakeStep("setup")}>
                  {t.source.continue}
                </ActionButton>
              </div>
            </WorkspacePanel>
          ) : null}

          {intakeStep === "setup" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">{t.steps.setup}</h2>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {t.setup.body}
                </p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Field className="md:col-span-2">
                  <label htmlFor="speaker-labels" className="block text-sm font-semibold text-ink">{t.setup.speakerLabels}</label>
                  <textarea
                    id="speaker-labels"
                    value={transcriptSetup.speakerLabels}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, speakerLabels: event.target.value }))}
                    className={`${controlClass} min-h-28`}
                  />
                </Field>
                <Field className="md:col-span-2">
                  <label htmlFor="session-metadata" className="block text-sm font-semibold text-ink">{t.setup.metadata}</label>
                  <textarea
                    id="session-metadata"
                    value={transcriptSetup.sessionMetadata}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, sessionMetadata: event.target.value }))}
                    className={`${controlClass} min-h-28`}
                  />
                </Field>
                <Field>
                  <label htmlFor="transcript-language" className="block text-sm font-semibold text-ink">{t.setup.language}</label>
                  <select
                    id="transcript-language"
                    value={transcriptSetup.language}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, language: event.target.value }))}
                    className={controlClass}
                  >
                    <option value="eng">{t.setup.languages.eng}</option>
                    <option value="tha">{t.setup.languages.tha}</option>
                    <option value="mixed">{t.setup.languages.mixed}</option>
                  </select>
                </Field>
                <Field>
                  <label htmlFor="sample-type" className="block text-sm font-semibold text-ink">{t.setup.sampleType}</label>
                  <select
                    id="sample-type"
                    value={transcriptSetup.sampleType}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, sampleType: event.target.value }))}
                    className={controlClass}
                  >
                    <option value="conversation">{t.setup.sampleTypes.conversation}</option>
                    <option value="play">{t.setup.sampleTypes.play}</option>
                    <option value="narrative">{t.setup.sampleTypes.narrative}</option>
                  </select>
                </Field>
              </div>
              <div className="space-y-3 rounded-panel border border-line bg-surface p-4">
                <p className="text-sm font-semibold text-ink">{t.setup.requirements}</p>
                <label className="flex min-h-11 items-start gap-3 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={transcriptSetup.reviewSpeakerLabels}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, reviewSpeakerLabels: event.target.checked }))}
                    aria-label={t.setup.reviewSpeakerLabels}
                    className="mt-1 h-4 w-4 rounded border-line"
                  />
                  <span>{t.setup.reviewSpeakerLabels}</span>
                </label>
                <label className="flex min-h-11 items-start gap-3 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={transcriptSetup.reviewFeatureLock}
                    onChange={(event) => setTranscriptSetup((current) => ({ ...current, reviewFeatureLock: event.target.checked }))}
                    aria-label={t.setup.reviewFeatureLock}
                    className="mt-1 h-4 w-4 rounded border-line"
                  />
                  <span>{t.setup.reviewFeatureLock}</span>
                </label>
              </div>
              <div className="flex flex-wrap justify-between gap-3">
                <ActionButton type="button" tone="ghost" onClick={() => setIntakeStep("source")}>
                  {t.setup.back}
                </ActionButton>
                <ActionButton type="button" onClick={() => setIntakeStep("review")}>
                  {t.setup.continue}
                </ActionButton>
              </div>
            </WorkspacePanel>
          ) : null}

          {intakeStep === "review" ? (
            <WorkspacePanel className="space-y-5 p-5 sm:p-6">
              <div>
                <h2 className="text-xl font-semibold text-ink">{t.steps.review}</h2>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  {t.review.body}
                </p>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <ReviewSummaryCard title={t.review.sessionSummary} rows={[
                  { label: t.review.childClient, value: sessionDetails.childClient || t.review.notSet },
                  { label: t.review.date, value: sessionDetails.sessionDate || t.review.notSet },
                  { label: t.review.time, value: sessionDetails.sessionTime || t.review.notSet },
                  { label: t.review.setting, value: t.details.settings[sessionDetails.setting] ?? sessionDetails.setting },
                  { label: t.review.duration, value: t.details.minutes(sessionDetails.durationMinutes) },
                  { label: t.review.clinician, value: sessionDetails.clinician || t.review.notSet }
                ]} />
                <ReviewSummaryCard title={t.review.workflowSummary} rows={[
                  { label: t.review.sourceType, value: t.sources[selectedSource] },
                  { label: t.review.transcriptSource, value: sourceReadyForReview ? t.review.sourceReady : t.review.sourceNotReady },
                  { label: t.review.language, value: t.setup.languages[transcriptSetup.language] ?? transcriptSetup.language },
                  { label: t.review.sampleType, value: t.setup.sampleTypes[transcriptSetup.sampleType] ?? transcriptSetup.sampleType },
                  { label: t.review.goals, value: sessionDetails.sessionGoals || t.review.notSet }
                ]} />
              </div>
              <SafetyNotice>
                {safety.DECISION_SUPPORT_ONLY} {t.review.safetyNote}
              </SafetyNotice>
              {selectedSource === "audio" || selectedSource === "recording" ? (
                <div className="rounded-panel border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-4 text-sm text-[color:var(--color-warning-text)]">
                  {t.review.asrWarning}
                </div>
              ) : null}
              <div className="flex flex-wrap justify-between gap-3">
                <ActionButton type="button" tone="ghost" onClick={() => setIntakeStep("setup")}>
                  {t.review.back}
                </ActionButton>
                <div className="flex flex-wrap gap-3">
                  <ActionButton type="button" tone="secondary" onClick={saveSessionIntakeDraft}>
                    {t.review.save}
                  </ActionButton>
                  <ActionButton
                    type="button"
                    onClick={() => {
                      const savedState = saveSessionIntakeDraft();
                      if (selectedSource === "paste" || selectedSource === "cha") {
                        void handleTranscriptSubmit(selectedSource === "paste" ? "paste-transcript" : "cha-upload");
                        return;
                      }
                      if (state.transcriptReady) {
                        router.push(workflowSessionHref("transcript", savedState));
                      }
                    }}
                    disabled={!canStartTranscriptReview}
                    aria-describedby={startTranscriptReviewBlockedReasonText ? "start-transcript-review-reason" : undefined}
                  >
                    {t.review.start}
                  </ActionButton>
                </div>
                {startTranscriptReviewBlockedReasonText ? (
                  <p
                    id="start-transcript-review-reason"
                    role="status"
                    className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]"
                  >
                    {startTranscriptReviewBlockedReasonText}
                  </p>
                ) : null}
              </div>
            </WorkspacePanel>
          ) : null}
    </>
  );
}
