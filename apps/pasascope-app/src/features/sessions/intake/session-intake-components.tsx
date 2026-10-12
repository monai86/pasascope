"use client";

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Check, CheckCircle2, ClipboardPaste, FileText, Sparkles } from "lucide-react";

import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";
import { sessionCompletion } from "@/features/sessions/state/session-completion";
import { sessionMessages } from "@/features/sessions/session.messages";
import { resolveSessionHref, sessionViews, type SessionView } from "@/features/sessions/state/session-view";
import { intakeMessages } from "@/features/sessions/intake/intake.messages";
import { useMessages } from "@/i18n/locale-provider";
import type { WorkflowSource, WorkflowState } from "@/lib/workflow";

export function workflowSessionHref(view: "intake" | "transcript" | "findings" | "report", state: WorkflowState, reportId?: string) {
  return resolveSessionHref(view, state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId, {
    caseId: state.caseId,
    transcriptId: state.backendTranscriptId,
    reportId: reportId ?? state.backendReportId ?? state.reportId,
  });
}

export function isTranscriptUnlocked(state: WorkflowState) {
  return state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
}


export function Field({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`.trim()}>
      {children}
    </div>
  );
}

export function SourceChoiceButton({
  label,
  active,
  icon: Icon,
  onClick
}: {
  label: string;
  active: boolean;
  icon: LucideIcon;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex min-h-24 flex-col items-start justify-between rounded-card border px-4 py-4 text-left transition motion-reduce:transition-none ${
        active
          ? "border-tint-strong bg-brand-soft text-brand-strong"
          : "border-line bg-surface text-ink"
      }`}
      aria-pressed={active}
    >
      <Icon size={20} aria-hidden="true" />
      <span className="text-sm font-semibold">{label}</span>
    </button>
  );
}

export function ReviewSummaryCard({
  title,
  rows
}: {
  title: string;
  rows: Array<{ label: string; value: string }>;
}) {
  return (
    <WorkspacePanel className="p-5">
      <h3 className="font-bold text-ink">{title}</h3>
      <dl className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={`${title}-${row.label}`} className="grid gap-1 border-b border-line/70 pb-3 last:border-b-0 last:pb-0">
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{row.label}</dt>
            <dd className="text-sm text-ink">{row.value}</dd>
          </div>
        ))}
      </dl>
    </WorkspacePanel>
  );
}


const SAMPLE_THAI_TRANSCRIPT = [
  "@Begin",
  "@Languages:\ttha",
  "@Participants:\tCHI น้องมิน Target_Child, THER นักบำบัด Investigator",
  "*THER:\tวันนี้หนูเล่นอะไรมาบ้างครับ?",
  "*CHI:\tหนู เล่น รถ ไฟ คัน ใหญ่ สี แดง ครับ.",
  "*THER:\tรถไฟวิ่งเร็วไหมนะ?",
  "*CHI:\tวิ่ง เร็ว มาก เลย ครับ.",
  "*THER:\tในรถไฟมีใครนั่งอยู่บ้าง?",
  "*CHI:\tมี คุณ พ่อ คุณ แม่ แล้ว ก็ น้อง มิน ครับ.",
  "*THER:\tเก่งมากครับ แล้วจะไปเที่ยวที่ไหนกันต่อ?",
  "*CHI:\tไป เที่ยว สวน สัตว์ ดู ช้าง ครับ.",
  "@End"
].join("\n");

const SAMPLE_ENG_TRANSCRIPT = [
  "@Begin",
  "@Languages:\teng",
  "@Participants:\tCHI Target_Child, THER Investigator",
  "*THER:\tWhat do you see?",
  "*CHI:\tI see a big blue block.",
  "*THER:\tWhat color is it?",
  "*CHI:\tIt is blue.",
  "*THER:\tCan you ask me a question?",
  "*CHI:\tWhat color do you like?",
  "@End"
].join("\n");

export function SourceInputPanel({
  mode,
  draftTranscript,
  busy,
  error,
  warnings,
  validationIssues,
  onDraftChange,
  onChaFile,
  onTranscriptSubmit
}: {
  mode?: string;
  draftTranscript: string;
  busy: boolean;
  error: string;
  warnings: string[];
  validationIssues: string[];
  onDraftChange: (value: string) => void;
  onChaFile: (file: File) => void;
  onTranscriptSubmit: (source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">) => void;
}) {
  const t = useMessages(intakeMessages);
  if (mode === "audio") {
    // Uploading an existing audio file is not built. Saying so is better than
    // a button that records an upload which never happened.
    return (
      <WorkspacePanel className="p-5">
        <h2 className="font-bold text-ink">{t.sourceChoices.audio}</h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          {t.source.audioBody}
        </p>
      </WorkspacePanel>
    );
  }

  if (mode === "cha" || mode === "paste") {
    const source = mode === "cha" ? "cha-upload" : "paste-transcript";
    return (
      <WorkspacePanel className="p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {mode === "cha" ? <FileText size={22} aria-hidden="true" className="text-highlight" /> : <ClipboardPaste size={22} aria-hidden="true" className="text-brand" />}
            <h2 className="font-bold text-ink">{mode === "cha" ? t.sourceChoices.cha : t.sourceChoices.paste}</h2>
          </div>
          {mode === "paste" && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-ink-muted font-medium">{t.source.quickDemo}</span>
              <button
                type="button"
                onClick={() => onDraftChange(SAMPLE_THAI_TRANSCRIPT)}
                className="inline-flex min-h-10 items-center gap-1 rounded-full border border-line-strong bg-surface-soft px-3 py-1 font-semibold text-ink transition hover:bg-surface-muted"
                title={t.source.thaiSampleTitle}
              >
                <Sparkles size={13} aria-hidden="true" />
                {t.source.thaiSample}
              </button>
              <button
                type="button"
                onClick={() => onDraftChange(SAMPLE_ENG_TRANSCRIPT)}
                className="inline-flex min-h-10 items-center gap-1 rounded-full border border-line-strong bg-surface-soft px-3 py-1 font-semibold text-ink transition hover:bg-surface-muted"
                title={t.source.englishSampleTitle}
              >
                {t.source.englishSample}
              </button>
            </div>
          )}
        </div>
        {mode === "cha" ? (
          <>
            <label className="sr-only" htmlFor="cha-transcript-file">{t.source.chaFileLabel}</label>
            <input
              id="cha-transcript-file"
              type="file"
              accept=".cha"
              className="mb-3 block w-full rounded-panel border border-line bg-surface px-3 py-3 text-sm"
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                if (file) void onChaFile(file);
              }}
            />
          </>
        ) : null}
        <textarea
          className="min-h-44 w-full rounded-panel border border-line bg-surface p-3 text-sm text-ink outline-none focus:ring-2 focus:ring-brand"
          value={draftTranscript}
          onChange={(event) => onDraftChange(event.target.value)}
          aria-label={mode === "cha" ? t.source.chaTextLabel : t.source.pasteTextLabel}
          aria-describedby={error ? "source-transcript-error" : undefined}
          data-testid="transcript-input"
        />
        {error ? (
          <p id="source-transcript-error" className="mt-3 rounded-card border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] p-3 text-sm font-semibold text-[color:var(--color-danger-text)] animate-fade-in" role="alert">
            {error}
          </p>
        ) : null}
        {warnings.length > 0 ? (
          <div className="mt-3 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]" role="status">
            <p className="font-semibold">{t.source.importWarnings}</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
          </div>
        ) : null}
        {validationIssues.length > 0 ? (
          <div className="mt-3 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]" role="alert">
            <p className="font-semibold">{t.source.chatValidation}</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{validationIssues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          </div>
        ) : null}
        <PrimaryActionButton
          icon={CheckCircle2}
          className="mt-3 w-full"
          onClick={() => onTranscriptSubmit(source)}
          disabled={busy || Boolean(error)}
          data-testid="save-transcript-button"
          aria-describedby={error ? "source-transcript-error" : undefined}
        >
          {t.source.saveTranscript}
        </PrimaryActionButton>
      </WorkspacePanel>
    );
  }

  return null;
}


/**
 * Where this session stands, from persisted state only: each step is marked
 * done when its own evidence exists, with a link to the first step that is
 * not. It shows no scores; those belong to Findings.
 */
export function SessionProgressCard({ state }: { state: WorkflowState }) {
  const t = useMessages(sessionMessages).progress;
  const completion = sessionCompletion(state);
  const next = sessionViews.find((view) => view !== "intake" && !completion[view]) as Exclude<SessionView, "intake"> | undefined;

  return (
    <WorkspacePanel className="hidden p-5 lg:block">
      <h2 className="text-lg font-semibold text-ink">{t.title}</h2>
      <ol className="mt-4 space-y-2" role="list">
        {sessionViews.map((view) => (
          <li key={view} className="flex items-center gap-3 rounded-control border border-line bg-surface-soft px-3 py-2.5 text-sm font-medium text-ink">
            <span
              aria-hidden="true"
              className={`grid h-6 w-6 shrink-0 place-items-center rounded-full ${completion[view] ? "bg-brand text-white" : "border border-line-strong bg-surface text-ink-subtle"}`}
            >
              {completion[view] ? <Check size={13} strokeWidth={3} /> : null}
            </span>
            <span className="min-w-0 flex-1">{t.steps[view]}</span>
            <span className="text-xs font-normal text-ink-subtle">{completion[view] ? t.done : t.notYet}</span>
          </li>
        ))}
      </ol>
      {completion.intake && next ? (
        <PrimaryActionButton href={workflowSessionHref(next, state)} icon={FileText} className="mt-4 w-full">
          {t.next[next]}
        </PrimaryActionButton>
      ) : null}
    </WorkspacePanel>
  );
}

export function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  if (!state.statusMessage && !state.error) {
    return null;
  }
  const isError = Boolean(state.error);
  const isSuccess = Boolean(state.statusMessage && !isError);
  if (isSuccess && backendUnavailable) {
    return null;
  }
  const className = isError
    ? "rounded-card border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] p-4 text-sm text-[color:var(--color-danger-text)] animate-fade-in"
    : isSuccess
      ? "rounded-card border border-[color:var(--color-info-border)] bg-[color:var(--color-info-bg)] p-4 text-sm text-[color:var(--color-info-text)] animate-fade-in"
      : "demo-note rounded-card p-4 text-sm";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}

