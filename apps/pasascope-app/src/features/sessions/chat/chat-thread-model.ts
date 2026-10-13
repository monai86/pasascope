import type { AnalysisStatus, FeatureSignal, TranscriptLine, WorkflowState } from "@/lib/workflow";

/**
 * The conversation for one session, derived from what is true of the session.
 *
 * Nothing here is a stored message. Every item follows from workflow state, so
 * a reload rebuilds the same thread and the backend stays the source of truth.
 * The model names kinds and carries facts; the view turns them into words in
 * the interface language, so there is no display text here.
 */

export const chatSteps = ["audio", "transcript", "measures", "report"] as const;
export type ChatStep = (typeof chatSteps)[number];

export type ChatSource = "recording" | "audio";
export type UploadStep = "idle" | "confirm" | "uploading" | "polling" | "done" | "error";
export type AssignableSpeaker = "CHI" | "THER";

export type ReplyAction =
  | "upload-audio"
  | "discard-audio"
  | "retry-audio"
  | "assign-therapist"
  | "assign-child"
  | "open-transcript"
  | "extract-measures"
  | "open-measures"
  | "generate-report"
  | "open-report"
  | "retry-save";

/** Why a reply cannot be used yet. The view supplies the sentence. */
export type BlockedReason = "no-child-lines" | "unsaved-transcript";

export type Reply = {
  action: ReplyAction;
  /** The one reply that moves the session forward. */
  primary?: boolean;
  blocked?: BlockedReason;
};

export type PreviewLine = {
  lineId: string;
  speaker: "child" | "therapist" | "unknown" | "other";
  /** The speaker code as written, for a speaker that is neither child nor therapist. */
  speakerCode: string;
  startMs?: number;
  text: string;
};

export type Measures = {
  /** Mean length of utterance in words. `null` when the backend sent no value. */
  mlu: number | null;
  totalWords: number | null;
  distinctWords: number | null;
  childUtterances: number | null;
  /** The same case's MLU in the session before this one, when there is one. */
  previousMlu: number | null;
};

export type ThreadItem =
  | { id: string; role: "user"; kind: "audio"; durationSeconds: number | null }
  | { id: string; role: "user"; kind: "transcript-file" }
  | { id: string; role: "user"; kind: "action"; action: "assigned-therapist" | "assigned-child" | "extract" | "report"; count?: number }
  | { id: string; role: "assistant"; kind: "loading" }
  | { id: string; role: "assistant"; kind: "load-failed" }
  | { id: string; role: "assistant"; kind: "consent-inactive" }
  | { id: string; role: "assistant"; kind: "ask-audio"; source: ChatSource }
  | { id: string; role: "assistant"; kind: "confirm-upload"; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "transcribing"; uploading: boolean }
  | { id: string; role: "assistant"; kind: "transcription-failed"; unavailable: boolean; replies: Reply[] }
  | {
      id: string;
      role: "assistant";
      kind: "transcript-ready";
      lineCount: number;
      unknownCount: number;
      preview: PreviewLine[];
      replies: Reply[];
    }
  | { id: string; role: "assistant"; kind: "save-failed"; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "speakers-complete"; assigned: boolean; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "measuring" }
  | { id: string; role: "assistant"; kind: "measures-failed"; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "measures-stale"; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "measures"; measures: Measures; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "reporting" }
  | { id: string; role: "assistant"; kind: "report-failed"; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "report-stale"; replies: Reply[] }
  | { id: string; role: "assistant"; kind: "report-ready"; signed: boolean; replies: Reply[] };

export type SessionThread = {
  items: ThreadItem[];
  /** The step the session is on: the first one not yet complete. */
  step: ChatStep;
  completed: Record<ChatStep, boolean>;
};

export type ChatFacts = {
  /** The session is still being read from the backend. */
  loading: boolean;
  /** The session could not be read. */
  loadFailed: boolean;
  consentGranted: boolean;
  source: ChatSource;
  audio: {
    step: UploadStep;
    /** Length of the recording or file in hand, when known. */
    durationSeconds: number | null;
    /** The server has no speech recognition switched on. */
    unavailable: boolean;
  };
  transcript: {
    ready: boolean;
    lines: readonly TranscriptLine[];
    saveStatus: WorkflowState["transcriptSaveStatus"];
    /** The transcript came from a file, not from audio. */
    fromFile: boolean;
  };
  analysis: {
    status: AnalysisStatus;
    extracted: boolean;
    signals: readonly FeatureSignal[];
    previousMlu: number | null;
  };
  report: {
    status: WorkflowState["reportStatus"];
    saveStatus: WorkflowState["reportSaveStatus"];
  };
  /** Set while this visit's "set all to…" is the reason every line has a speaker. */
  assignment: { speaker: AssignableSpeaker; count: number } | null;
};

// Each measure under every name an extractor in this repository gives it. The
// list mirrors TREND_FEATURES in apps/api/app/api/v1/routes/dashboard.py.
const MEASURE_NAMES = {
  mlu: ["mean_length_of_utterance_words", "mluw", "mlu_w", "mlu", "mlu_words"],
  totalWords: ["total_word_count", "total_words"],
  distinctWords: ["number_of_different_words", "ndw"],
  childUtterances: ["child_utterance_count"],
} as const;

export function isUnknownSpeaker(line: Pick<TranscriptLine, "speaker">): boolean {
  return !line.speaker.trim() || line.speaker === "UNK";
}

export function isChildSpeaker(line: Pick<TranscriptLine, "speaker">): boolean {
  return line.speaker.trim().toUpperCase() === "CHI";
}

/** Every line without a speaker set to the therapist's choice; the others untouched. */
export function assignUnknownSpeakers(lines: readonly TranscriptLine[], speaker: AssignableSpeaker): TranscriptLine[] {
  return lines.map((line) => (isUnknownSpeaker(line) ? { ...line, speaker } : line));
}

/**
 * A value the backend computed, or `null`. A missing or non-numeric value is
 * never replaced by a default: the card shows a blank instead.
 */
function measure(signals: readonly FeatureSignal[], names: readonly string[]): number | null {
  for (const name of names) {
    const raw = signals.find((signal) => signal.featureName === name)?.rawValue;
    if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  }
  return null;
}

export function readMeasures(signals: readonly FeatureSignal[], previousMlu: number | null): Measures {
  return {
    mlu: measure(signals, MEASURE_NAMES.mlu),
    totalWords: measure(signals, MEASURE_NAMES.totalWords),
    distinctWords: measure(signals, MEASURE_NAMES.distinctWords),
    childUtterances: measure(signals, MEASURE_NAMES.childUtterances),
    previousMlu,
  };
}

function previewSpeaker(line: TranscriptLine): PreviewLine["speaker"] {
  if (isUnknownSpeaker(line)) return "unknown";
  if (isChildSpeaker(line)) return "child";
  return line.speaker.trim().toUpperCase() === "THER" ? "therapist" : "other";
}

function toPreview(line: TranscriptLine): PreviewLine {
  return {
    lineId: line.lineId,
    speaker: previewSpeaker(line),
    speakerCode: line.speaker,
    startMs: line.startMs,
    text: line.text,
  };
}

/**
 * Two lines that show what the transcript is like: the first thing the child
 * says, and the first line still without a speaker (or, when every line has
 * one, the line after the child's).
 */
function previewOf(lines: readonly TranscriptLine[]): PreviewLine[] {
  const spoken = lines.filter((line) => line.text.trim());
  const child = spoken.find(isChildSpeaker);
  const unknown = spoken.find(isUnknownSpeaker);
  const first = child ?? spoken[0];
  if (!first) return [];
  const second = unknown && unknown !== first ? unknown : spoken[spoken.indexOf(first) + 1] ?? spoken.find((line) => line !== first);
  return [first, second].filter((line): line is TranscriptLine => Boolean(line)).map(toPreview);
}

export function buildSessionThread(facts: ChatFacts): SessionThread {
  const lines = facts.transcript.lines;
  const unknownCount = lines.filter(isUnknownSpeaker).length;
  const childCount = lines.filter(isChildSpeaker).length;
  const speakersComplete = facts.transcript.ready && lines.length > 0 && unknownCount === 0;
  const reportExists = facts.report.status === "draft" || facts.report.status === "reviewed" || facts.report.status === "finalized";
  const completed: Record<ChatStep, boolean> = {
    audio: facts.transcript.ready,
    // Measures taken from the transcript mean its review is behind us.
    transcript: speakersComplete || facts.analysis.extracted,
    measures: facts.analysis.extracted,
    report: reportExists,
  };
  const step = chatSteps.find((candidate) => !completed[candidate]) ?? "report";
  const done = (items: ThreadItem[]): SessionThread => ({ items, step, completed });

  if (facts.loading) return done([{ id: "loading", role: "assistant", kind: "loading" }]);
  if (facts.loadFailed) return done([{ id: "load-failed", role: "assistant", kind: "load-failed" }]);

  const items: ThreadItem[] = [];
  const audioChip: ThreadItem = { id: "audio", role: "user", kind: "audio", durationSeconds: facts.audio.durationSeconds };

  // Step 1: getting a transcript.
  if (!facts.transcript.ready) {
    // Consent can be withdrawn after a session exists; nothing is collected then.
    if (!facts.consentGranted) return done([{ id: "consent-inactive", role: "assistant", kind: "consent-inactive" }]);

    switch (facts.audio.step) {
      case "confirm":
        items.push(audioChip, {
          id: "confirm-upload",
          role: "assistant",
          kind: "confirm-upload",
          replies: [{ action: "upload-audio", primary: true }, { action: "discard-audio" }],
        });
        break;
      case "uploading":
      case "polling":
      // The job has finished and the transcript is about to arrive.
      case "done":
        items.push(audioChip, {
          id: "transcribing",
          role: "assistant",
          kind: "transcribing",
          uploading: facts.audio.step === "uploading",
        });
        break;
      case "error":
        items.push(audioChip, {
          id: "transcription-failed",
          role: "assistant",
          kind: "transcription-failed",
          unavailable: facts.audio.unavailable,
          replies: [{ action: "retry-audio", primary: true }],
        });
        break;
      default:
        items.push({ id: "ask-audio", role: "assistant", kind: "ask-audio", source: facts.source });
    }
    return done(items);
  }

  // Step 2: the transcript and who is speaking.
  items.push(facts.transcript.fromFile ? { id: "transcript-file", role: "user", kind: "transcript-file" } : audioChip);

  const settled = facts.analysis.extracted || facts.analysis.status === "processing";
  const transcriptReplies: Reply[] = settled || speakersComplete
    ? []
    : unknownCount === lines.length
      // Nothing is labelled, so there is no "the rest" to set in one go: the
      // speakers have to be told apart on the transcript itself.
      ? [{ action: "open-transcript", primary: true }]
      : [{ action: "assign-therapist" }, { action: "assign-child" }, { action: "open-transcript" }];
  items.push({
    id: "transcript-ready",
    role: "assistant",
    kind: "transcript-ready",
    lineCount: lines.length,
    unknownCount,
    preview: previewOf(lines),
    replies: transcriptReplies,
  });

  if (facts.transcript.saveStatus === "failed") {
    items.push({ id: "save-failed", role: "assistant", kind: "save-failed", replies: [{ action: "retry-save", primary: true }] });
    return done(items);
  }

  if (speakersComplete) {
    if (facts.assignment) {
      items.push({
        id: "assigned",
        role: "user",
        kind: "action",
        action: facts.assignment.speaker === "THER" ? "assigned-therapist" : "assigned-child",
        count: facts.assignment.count,
      });
    }
    const blocked: BlockedReason | undefined = childCount === 0
      ? "no-child-lines"
      : facts.transcript.saveStatus !== "saved"
        ? "unsaved-transcript"
        : undefined;
    items.push({
      id: "speakers-complete",
      role: "assistant",
      kind: "speakers-complete",
      assigned: Boolean(facts.assignment),
      replies: settled || facts.analysis.status === "stale" || facts.analysis.status === "failed"
        ? []
        : [{ action: "extract-measures", primary: true, blocked }, { action: "open-transcript" }],
    });
  }

  // Step 3: descriptive measures.
  if (facts.analysis.status === "processing") {
    items.push({ id: "extract", role: "user", kind: "action", action: "extract" }, { id: "measuring", role: "assistant", kind: "measuring" });
    return done(items);
  }
  if (facts.analysis.status === "failed") {
    items.push(
      { id: "extract", role: "user", kind: "action", action: "extract" },
      { id: "measures-failed", role: "assistant", kind: "measures-failed", replies: [{ action: "extract-measures", primary: true }] },
    );
    return done(items);
  }
  if (facts.analysis.status === "stale") {
    // The transcript changed after the measures were taken; the old values
    // are no longer about this transcript and are not shown.
    items.push({
      id: "measures-stale",
      role: "assistant",
      kind: "measures-stale",
      replies: speakersComplete
        ? [{ action: "extract-measures", primary: true, blocked: childCount === 0 ? "no-child-lines" : undefined }, { action: "open-transcript" }]
        : [{ action: "open-transcript", primary: true }],
    });
    return done(items);
  }
  if (!facts.analysis.extracted) return done(items);

  const reporting = facts.report.saveStatus === "saving";
  const reportFailed = facts.report.saveStatus === "failed" && !reportExists && facts.report.status !== "stale";
  items.push(
    { id: "extract", role: "user", kind: "action", action: "extract" },
    {
      id: "measures",
      role: "assistant",
      kind: "measures",
      measures: readMeasures(facts.analysis.signals, facts.analysis.previousMlu),
      // Only the latest message carries the reply that moves the session on.
      replies: reportExists || reporting || reportFailed || facts.report.status === "stale"
        ? [{ action: "open-measures" }, { action: "open-transcript" }]
        : [{ action: "generate-report", primary: true }, { action: "open-measures" }, { action: "open-transcript" }],
    },
  );

  // Step 4: the report draft.
  if (reporting) {
    items.push({ id: "report", role: "user", kind: "action", action: "report" }, { id: "reporting", role: "assistant", kind: "reporting" });
  } else if (facts.report.status === "stale") {
    items.push({ id: "report-stale", role: "assistant", kind: "report-stale", replies: [{ action: "generate-report", primary: true }] });
  } else if (reportExists) {
    items.push(
      { id: "report", role: "user", kind: "action", action: "report" },
      {
        id: "report-ready",
        role: "assistant",
        kind: "report-ready",
        signed: facts.report.status === "finalized",
        replies: [{ action: "open-report", primary: true }],
      },
    );
  } else if (reportFailed) {
    items.push(
      { id: "report", role: "user", kind: "action", action: "report" },
      { id: "report-failed", role: "assistant", kind: "report-failed", replies: [{ action: "generate-report", primary: true }] },
    );
  }

  return done(items);
}
