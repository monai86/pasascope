"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronRight, FileText, Info, Loader2, Mic, Upload } from "lucide-react";

import { audioCaptureMessages } from "@/components/audio-capture.messages";
import { BrowserAudioRecorder, type RecordingMetadata } from "@/components/browser-audio-recorder";
import { ChatComposer } from "@/components/chat-shell/chat-composer";
import {
  AssistantMessage,
  ChatBlockedReason,
  ChatComposerDock,
  ChatCard,
  ChatError,
  ChatNote,
  ChatThread,
  QuickReplies,
  QuickReply,
  UserBubble,
} from "@/components/chat-shell/chat-primitives";
import { ChatShellHeader, ChatShellPanel } from "@/components/chat-shell/chat-shell-context";
import { consentMessages } from "@/components/consent.messages";
import { SkeletonLine } from "@/components/skeleton";
import type { SessionContext } from "@/features/sessions/components/session-context-header";
import { chatMessages } from "@/features/sessions/chat/chat.messages";
import {
  buildSessionThread,
  chatSteps,
  isUnknownSpeaker,
  type AssignableSpeaker,
  type ChatFacts,
  type ChatSource,
  type Measures,
  type PreviewLine,
  type Reply,
  type ReplyAction,
  type ThreadItem,
  type UploadStep,
} from "@/features/sessions/chat/chat-thread-model";
import { takePendingSessionAudio } from "@/features/sessions/chat/pending-audio";
import { SessionContextPanel, clock } from "@/features/sessions/chat/session-context-panel";
import { usePreviousMlu } from "@/features/sessions/chat/use-previous-mlu";
import { formatNumber } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { useAppMode } from "@/lib/app-mode";
import { useSafetyCopy } from "@/lib/safety-copy";
import type { TranscriptLine, WorkflowState } from "@/lib/workflow";

const ATTACH_TYPES = "audio/*,.wav,.mp3,.m4a,.mp4,.webm,.ogg,.mov,.cha";
const AUDIO_TYPES = "audio/*,.wav,.mp3,.m4a,.mp4,.webm,.ogg,.mov";
// The hosted transcription service refuses anything larger.
const HOSTED_AUDIO_LIMIT_BYTES = 25 * 1024 * 1024;

export type SessionChatViewProps = {
  sessionContext: SessionContext;
  state: WorkflowState;
  /** The session has been read from the backend, or reading it has failed. */
  hydrated: boolean;
  busy: boolean;
  backendUnavailable: boolean;
  source: ChatSource;
  lines: TranscriptLine[];
  audioUrl?: string;
  /** The session's notes, one per line. */
  notes: string;
  summary: { caseCode?: string; ageMonths?: number; language?: string; sessionDate?: string };
  attachError: string;
  audio: {
    recorded: { blob: Blob; durationSeconds: number } | null;
    step: UploadStep;
    jobStatus: string;
    jobMessage: string;
    fileError?: "unsupported";
  };
  hrefs: { transcript: string; findings: string; report: string };
  onRecordingMetadata: (metadata: RecordingMetadata) => void;
  onRecordingReady: (blob: Blob, metadata: RecordingMetadata) => void;
  onAudioFile: (file: File) => void | Promise<void>;
  onDiscardAudio: () => void;
  onUploadAudio: () => void | Promise<void>;
  onAttachTranscript: (file: File) => void | Promise<void>;
  onAssignUnknownSpeakers: (speaker: AssignableSpeaker) => void | Promise<void>;
  onRetrySave: () => void | Promise<void>;
  onExtractMeasures: () => void | Promise<void>;
  onGenerateReport: () => void | Promise<void>;
  onSaveNote: (text: string) => Promise<boolean>;
};

type NoteEcho = { id: number; text: string; saved: boolean | null; after: string | undefined };

/**
 * One session as a conversation. The thread is rebuilt from session state on
 * every render; the only things kept here are what this visit alone knows:
 * which "set all" the therapist pressed, and the notes just typed.
 */
export function SessionChatView(props: SessionChatViewProps) {
  const { sessionContext, state, hydrated, busy, lines, audio, hrefs } = props;
  const t = useMessages(chatMessages);
  const { externalTranscription } = useAppMode();
  const [source, setSource] = useState<ChatSource>(props.source);
  const [assignment, setAssignment] = useState<ChatFacts["assignment"]>(null);
  const [pending, setPending] = useState<ReplyAction | null>(null);
  const [text, setText] = useState("");
  const [echoes, setEchoes] = useState<NoteEcho[]>([]);
  const end = useRef<HTMLDivElement>(null);
  const echoCount = useRef(0);

  const sessionId = sessionContext.sessionId;
  const consentGranted = sessionContext.consentStatus === "granted";
  const previousMlu = usePreviousMlu(sessionContext.caseId, sessionId, state.featuresExtracted ? state.featureSetId : undefined);
  // A transcript made by speech recognition carries its draft label; one
  // without it was attached or typed.
  const fromFile = state.transcriptReady && !state.transcriptDraftLabel;

  const thread = buildSessionThread({
    loading: !hydrated || state.workflowLoading,
    loadFailed: hydrated && !state.backendSessionId && Boolean(state.error),
    consentGranted,
    source,
    audio: {
      step: audio.step,
      durationSeconds: audio.recorded?.durationSeconds || null,
      unavailable: audio.jobStatus === "unavailable",
    },
    transcript: { ready: state.transcriptReady, lines, saveStatus: state.transcriptSaveStatus, fromFile },
    analysis: {
      status: state.analysisStatus,
      extracted: state.featuresExtracted,
      signals: state.featureSignals,
      previousMlu,
    },
    report: { status: state.reportStatus, saveStatus: state.reportSaveStatus },
    assignment,
  });

  // An audio file chosen on the home screen is handed over once the session is open.
  const onAudioFile = props.onAudioFile;
  useEffect(() => {
    if (!hydrated || !sessionId || state.transcriptReady) return;
    const file = takePendingSessionAudio(sessionId);
    if (file) {
      setSource("audio");
      void onAudioFile(file);
    }
    // Runs once per opened session; the handler identity changes every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, sessionId]);

  useEffect(() => {
    if (!busy) setPending(null);
  }, [busy]);

  const itemCount = thread.items.length + echoes.length;
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [itemCount]);

  const stepNumber = chatSteps.indexOf(thread.step) + 1;
  const tooLarge = externalTranscription && (audio.recorded?.blob.size ?? 0) > HOSTED_AUDIO_LIMIT_BYTES;

  function run(action: ReplyAction) {
    setPending(action);
    switch (action) {
      case "upload-audio":
        return void props.onUploadAudio();
      case "discard-audio":
      case "retry-audio":
        setPending(null);
        return props.onDiscardAudio();
      case "assign-therapist":
      case "assign-child": {
        const speaker: AssignableSpeaker = action === "assign-therapist" ? "THER" : "CHI";
        setAssignment({ speaker, count: lines.filter(isUnknownSpeaker).length });
        return void props.onAssignUnknownSpeakers(speaker);
      }
      case "retry-save":
        return void props.onRetrySave();
      case "extract-measures":
        return void props.onExtractMeasures();
      case "generate-report":
        return void props.onGenerateReport();
      default:
        setPending(null);
    }
  }

  const hrefFor: Partial<Record<ReplyAction, string>> = {
    "open-transcript": hrefs.transcript,
    "open-measures": hrefs.findings,
    "open-report": hrefs.report,
  };

  function replies(list: Reply[], reasonId: string): ReactNode {
    if (list.length === 0) return null;
    const blocked = list.find((reply) => reply.blocked)?.blocked;
    return (
      <>
        <QuickReplies>
          {list.map((reply) => {
            const href = hrefFor[reply.action];
            const label = t.replies[reply.action];
            const testId = `reply-${reply.action}`;
            if (href) {
              return <QuickReply key={reply.action} href={href} primary={reply.primary} testId={testId}>{label}</QuickReply>;
            }
            const sizeBlocked = reply.action === "upload-audio" && tooLarge;
            return (
              <QuickReply
                key={reply.action}
                primary={reply.primary}
                onClick={() => run(reply.action)}
                loading={pending === reply.action && busy}
                disabled={busy || Boolean(reply.blocked) || sizeBlocked}
                aria-describedby={reply.blocked ? reasonId : undefined}
                testId={testId}
              >
                {label}
              </QuickReply>
            );
          })}
        </QuickReplies>
        {blocked ? <ChatBlockedReason id={reasonId}>{t.blocked[blocked]}</ChatBlockedReason> : null}
      </>
    );
  }

  async function saveNote() {
    const note = text.trim();
    if (!note) return;
    echoCount.current += 1;
    const id = echoCount.current;
    setText("");
    setEchoes((current) => [...current, { id, text: note, saved: null, after: thread.items.at(-1)?.id }]);
    const saved = await props.onSaveNote(note);
    setEchoes((current) => current.map((echo) => (echo.id === id ? { ...echo, saved } : echo)));
  }

  function attach(file: File) {
    if (file.name.toLowerCase().endsWith(".cha")) return void props.onAttachTranscript(file);
    setSource("audio");
    void props.onAudioFile(file);
  }

  // Notes typed during this visit sit after the message they followed, so the
  // thread still reads in the order things happened.
  const lastId = thread.items.at(-1)?.id;
  const echoesAfter = (id: string) =>
    echoes.filter((echo) => (thread.items.some((item) => item.id === echo.after) ? echo.after : lastId) === id);

  return (
    <div className="flex flex-1 flex-col">
      <ChatShellHeader
        backHref="/"
        title={sessionContext.caseLabel || t.threadLabel}
        subtitle={t.stepOf(stepNumber, chatSteps.length)}
      />
      <ChatShellPanel triggerLabel={t.panel.trigger} triggerIcon={Info}>
        <SessionContextPanel
          summary={{
            caseLabel: sessionContext.caseLabel || t.threadLabel,
            caseCode: props.summary.caseCode,
            ageMonths: props.summary.ageMonths,
            language: props.summary.language,
            sessionDate: props.summary.sessionDate,
            consentGranted,
          }}
          step={thread.step}
          completed={thread.completed}
          audioUrl={props.audioUrl}
          notes={props.notes.split("\n").map((note) => note.trim()).filter(Boolean)}
        />
      </ChatShellPanel>

      <ChatThread
        label={t.threadLabel}
        heading={sessionContext.caseLabel ? t.heading(sessionContext.caseLabel) : t.threadLabel}
        className="flex-1 pb-6"
      >
        {thread.items.map((item) => (
          <ThreadEntry key={item.id}>
            <ThreadItemView
              item={item}
              view={props}
              source={source}
              onSourceChange={setSource}
              tooLarge={tooLarge}
              fromFile={fromFile}
              renderReplies={(list) => replies(list, `chat-reason-${item.id}`)}
            />
            {echoesAfter(item.id).map((echo) => (
              <NoteEchoView key={echo.id} echo={echo} />
            ))}
          </ThreadEntry>
        ))}
        {props.attachError ? (
          <AssistantMessage>
            <ChatError>{t.composer.attachFailed}</ChatError>
          </AssistantMessage>
        ) : null}
        <div ref={end} aria-hidden="true" className="scroll-mb-28" />
      </ChatThread>

      <ChatComposerDock>
        <ChatComposer
          testId="session-composer"
          label={t.composer.label}
          placeholder={t.composer.placeholder}
          submitLabel={t.composer.submit}
          value={text}
          onChange={setText}
          onSubmit={() => void saveNote()}
          disabled={!hydrated || !state.backendSessionId}
          attach={
            consentGranted && !state.transcriptReady && audio.step === "idle"
              ? { label: t.composer.attach, accept: ATTACH_TYPES, onFile: attach }
              : undefined
          }
        />
      </ChatComposerDock>
    </div>
  );
}

/** Keeps a message and the notes typed after it together as flex children of the thread. */
function ThreadEntry({ children }: { children: ReactNode }) {
  return <div className="flex flex-col gap-6">{children}</div>;
}

function NoteEchoView({ echo }: { echo: NoteEcho }) {
  const t = useMessages(chatMessages);
  return (
    <>
      <UserBubble testId="chat-note">
        <span className="block text-xs font-semibold text-ink-subtle">{t.said.note}</span>
        {echo.text}
      </UserBubble>
      {echo.saved === null ? null : (
        <AssistantMessage>
          {echo.saved ? <p>{t.composer.saved}</p> : <ChatError>{t.composer.failed}</ChatError>}
        </AssistantMessage>
      )}
    </>
  );
}

function Working({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="flex items-center gap-2.5">
      <Loader2 size={18} aria-hidden="true" className="shrink-0 animate-spin text-ink-subtle motion-reduce:animate-none" />
      <span>{children}</span>
    </p>
  );
}

function useElapsedSeconds(): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return seconds;
}

function Transcribing({ uploading }: { uploading: boolean }) {
  const t = useMessages(chatMessages).transcribing;
  const seconds = useElapsedSeconds();
  return (
    <AssistantMessage testId="chat-transcribing">
      <Working>{uploading ? t.uploading : t.working}</Working>
      <ChatNote>{t.elapsed(clock(seconds))}</ChatNote>
    </AssistantMessage>
  );
}

function ThreadItemView({
  item,
  view,
  source,
  onSourceChange,
  tooLarge,
  fromFile,
  renderReplies,
}: {
  item: ThreadItem;
  view: SessionChatViewProps;
  source: ChatSource;
  onSourceChange: (source: ChatSource) => void;
  tooLarge: boolean;
  fromFile: boolean;
  renderReplies: (replies: Reply[]) => ReactNode;
}) {
  const t = useMessages(chatMessages);
  const upload = useMessages(audioCaptureMessages).upload;
  const consent = useMessages(consentMessages);
  const safety = useSafetyCopy();
  const { externalTranscription } = useAppMode();
  const fileInput = useRef<HTMLInputElement>(null);

  switch (item.kind) {
    case "audio":
      return (
        <div
          data-chat-role="user"
          data-testid="chat-audio"
          className="flex items-center gap-2.5 self-end rounded-full bg-surface py-2 pl-2 pr-[18px] shadow-chat-card"
        >
          <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-navy text-white">
            <Mic size={18} />
          </span>
          <span className="flex flex-col leading-snug">
            <span className="font-semibold">{t.audioChip.title}</span>
            {item.durationSeconds ? (
              <span className="text-[13px] text-ink-subtle">{t.audioChip.minutes(clock(item.durationSeconds))}</span>
            ) : null}
          </span>
        </div>
      );

    case "transcript-file":
      return (
        <UserBubble testId="chat-transcript-file">
          <span className="flex items-center gap-2">
            <FileText size={18} aria-hidden="true" className="shrink-0 text-ink-subtle" />
            {t.transcriptFile}
          </span>
        </UserBubble>
      );

    case "action":
      return (
        <UserBubble testId={`chat-said-${item.action}`}>
          {item.action === "assigned-therapist"
            ? t.said.assignedTherapist(item.count ?? 0)
            : item.action === "assigned-child"
              ? t.said.assignedChild(item.count ?? 0)
              : t.said[item.action]}
        </UserBubble>
      );

    case "loading":
      return (
        <AssistantMessage>
          <div role="status" className="space-y-3">
            <span className="sr-only">{t.loading}</span>
            <SkeletonLine className="w-2/3" />
            <SkeletonLine className="w-1/2" />
          </div>
        </AssistantMessage>
      );

    case "load-failed":
      return (
        <AssistantMessage testId="chat-load-failed">
          <ChatError>{t.loadFailed}</ChatError>
          <QuickReplies>
            <QuickReply primary onClick={() => window.location.reload()}>{t.reload}</QuickReply>
          </QuickReplies>
        </AssistantMessage>
      );

    case "consent-inactive":
      return (
        <AssistantMessage testId="chat-consent-inactive">
          <p>{t.consentInactive}</p>
          {view.sessionContext.caseId ? (
            <QuickReplies>
              <QuickReply primary href={`/cases/${encodeURIComponent(view.sessionContext.caseId)}`}>{t.openCase}</QuickReply>
            </QuickReplies>
          ) : null}
        </AssistantMessage>
      );

    case "ask-audio":
      return (
        <AssistantMessage testId="chat-ask-audio">
          <p>{source === "recording" ? t.askAudio.recording : t.askAudio.audio}</p>
          {source === "recording" ? (
            <ChatCard className="p-[18px]">
              <BrowserAudioRecorder
                initialDurationSeconds={view.state.recordingSeconds}
                hadUnsavedRecording={view.state.hasUnsavedRecording}
                onMetadataChange={view.onRecordingMetadata}
                onRecordingReady={view.onRecordingReady}
                onRecordingCleared={view.onDiscardAudio}
              />
            </ChatCard>
          ) : (
            <ChatCard className="flex flex-col items-start gap-3 p-[18px]">
              <input
                ref={fileInput}
                type="file"
                accept={AUDIO_TYPES}
                className="sr-only"
                tabIndex={-1}
                aria-hidden="true"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (file) void view.onAudioFile(file);
                }}
              />
              <QuickReply primary icon={Upload} onClick={() => fileInput.current?.click()} testId="chat-choose-audio">
                {t.askAudio.chooseFile}
              </QuickReply>
              <ChatNote>{t.askAudio.formats}</ChatNote>
              {view.audio.fileError ? <ChatError>{t.askAudio.unsupported}</ChatError> : null}
            </ChatCard>
          )}
          <button
            type="button"
            onClick={() => onSourceChange(source === "recording" ? "audio" : "recording")}
            className="min-h-11 self-start rounded-full px-1 text-sm font-medium text-ink-muted underline-offset-4 transition hover:text-ink hover:underline focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
          >
            {source === "recording" ? t.askAudio.useFileInstead : t.askAudio.recordInstead}
          </button>
          <ChatNote>{t.askAudio.transcriptHint}</ChatNote>
        </AssistantMessage>
      );

    case "confirm-upload":
      return (
        <AssistantMessage testId="chat-confirm-upload">
          <p>{t.confirmUpload.ask}</p>
          {/* Where the audio goes is said before it leaves, not after. */}
          <ChatNote>{externalTranscription ? consent.externalTranscription : upload.privacyBody}</ChatNote>
          {tooLarge ? <ChatError>{t.confirmUpload.tooLarge}</ChatError> : null}
          {renderReplies(item.replies)}
          <ChatNote>{safety.EXPERIMENTAL_ASR_CAUTION}</ChatNote>
        </AssistantMessage>
      );

    case "transcribing":
      return <Transcribing uploading={item.uploading} />;

    case "transcription-failed":
      return (
        <AssistantMessage testId="chat-transcription-failed">
          <ChatError>{item.unavailable ? t.transcriptionFailed.unavailable : t.transcriptionFailed.failed}</ChatError>
          {!item.unavailable && view.audio.jobMessage ? <ChatNote>{view.audio.jobMessage}</ChatNote> : null}
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "transcript-ready":
      return (
        <AssistantMessage testId="chat-transcript-ready">
          <p>
            {item.lineCount === 0
              ? t.transcript.empty
              : [
                  fromFile ? t.transcript.readyFromFile(item.lineCount) : t.transcript.ready(item.lineCount),
                  item.unknownCount === 0
                    ? ""
                    : item.unknownCount === item.lineCount
                      ? t.transcript.unknownAll
                      : t.transcript.unknownSome(item.unknownCount),
                ].filter(Boolean).join(" ")}
          </p>
          <ChatCard>
            {item.preview.map((line) => (
              <PreviewLineView key={line.lineId} line={line} />
            ))}
            <Link
              href={view.hrefs.transcript}
              className="flex min-h-12 items-center justify-between border-t border-chat-line px-[18px] text-sm font-semibold text-ink transition first:border-t-0 hover:bg-chat-frame focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
            >
              {t.transcript.viewAll}
              <ChevronRight size={18} aria-hidden="true" />
            </Link>
          </ChatCard>
          {fromFile ? null : <ChatNote>{safety.EXPERIMENTAL_ASR_CAUTION}</ChatNote>}
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "save-failed":
      return (
        <AssistantMessage testId="chat-save-failed">
          <ChatError>{t.saveFailed}</ChatError>
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "speakers-complete":
      return (
        <AssistantMessage testId="chat-speakers-complete">
          <p>{item.assigned ? t.speakersComplete.assigned : t.speakersComplete.ready}</p>
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "measuring":
      return (
        <AssistantMessage testId="chat-measuring">
          <Working>{t.measuring}</Working>
        </AssistantMessage>
      );

    case "measures-failed":
      return (
        <AssistantMessage testId="chat-measures-failed">
          <ChatError>{t.measuresFailed}</ChatError>
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "measures-stale":
      return (
        <AssistantMessage testId="chat-measures-stale">
          <p>{t.measuresStale}</p>
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "measures":
      return (
        <AssistantMessage testId="chat-measures">
          <p>{t.measures.intro(item.measures.childUtterances)}</p>
          <MeasuresCard measures={item.measures} />
          <ChatNote>
            {t.measures.descriptive} {safety.THERAPIST_INTERPRETATION_REQUIRED}
          </ChatNote>
          {/* Shown only beside a previous session's value, which is what it is about. */}
          {item.measures.previousMlu === null ? null : <ChatNote>{safety.LONGITUDINAL_DELTA_CAUTION}</ChatNote>}
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "reporting":
      return (
        <AssistantMessage testId="chat-reporting">
          <Working>{t.reporting}</Working>
        </AssistantMessage>
      );

    case "report-failed":
      return (
        <AssistantMessage testId="chat-report-failed">
          <ChatError>{t.reportFailed}</ChatError>
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "report-stale":
      return (
        <AssistantMessage testId="chat-report-stale">
          <p>{t.reportStale}</p>
          {renderReplies(item.replies)}
        </AssistantMessage>
      );

    case "report-ready":
      return (
        <AssistantMessage testId="chat-report-ready">
          <p>{item.signed ? t.reportReady.signed : t.reportReady.draft}</p>
          {renderReplies(item.replies)}
        </AssistantMessage>
      );
  }
}

function PreviewLineView({ line }: { line: PreviewLine }) {
  const t = useMessages(chatMessages).transcript.speakers;
  const speaker =
    line.speaker === "child" ? t.child : line.speaker === "therapist" ? t.therapist : line.speaker === "unknown" ? t.unknown : line.speakerCode;
  const time = typeof line.startMs === "number" ? ` · ${clock(line.startMs / 1000)}` : "";

  return (
    <div className="border-t border-chat-line px-[18px] py-3.5 first:border-t-0">
      <span className={line.speaker === "unknown" ? "text-xs font-semibold text-highlight-text" : "text-xs text-ink-subtle"}>
        {speaker}
        {time}
      </span>
      <p className="text-base">{line.text}</p>
    </div>
  );
}

function MeasuresCard({ measures }: { measures: Measures }) {
  const t = useMessages(chatMessages).measures;
  const { locale } = useLocale();
  // A value the backend did not send is shown as a dash, never as a number.
  const show = (value: number | null, digits = 0) =>
    value === null ? (
      <>
        <span aria-hidden="true">—</span>
        <span className="sr-only">{t.noValue}</span>
      </>
    ) : (
      formatNumber(value, locale, { maximumFractionDigits: digits })
    );

  return (
    <ChatCard className="flex flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:gap-7">
      <div className="flex-1">
        <p className="text-[13px] text-ink-subtle">{t.mlu}</p>
        <p data-testid="measure-mlu" className="font-display text-[56px] font-semibold leading-[1.15] text-ink">
          {show(measures.mlu, 2)}
        </p>
        <p className="text-ink-subtle">
          {t.mluUnit}
          {measures.previousMlu === null
            ? ""
            : ` · ${t.previous(formatNumber(measures.previousMlu, locale, { maximumFractionDigits: 2 }))}`}
        </p>
      </div>
      <div className="flex gap-7 border-t border-chat-line pt-4 sm:flex-col sm:gap-3 sm:border-l sm:border-t-0 sm:pl-7 sm:pt-0">
        <div>
          <p data-testid="measure-total-words" className="font-display text-2xl font-semibold leading-snug text-ink">
            {show(measures.totalWords)}
          </p>
          <p className="text-[13px] text-ink-subtle">{t.totalWords}</p>
        </div>
        <div>
          <p data-testid="measure-distinct-words" className="font-display text-2xl font-semibold leading-snug text-ink">
            {show(measures.distinctWords)}
          </p>
          <p className="text-[13px] text-ink-subtle">{t.distinctWords}</p>
        </div>
      </div>
    </ChatCard>
  );
}
