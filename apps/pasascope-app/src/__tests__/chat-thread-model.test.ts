import { describe, expect, it } from "vitest";

import {
  assignUnknownSpeakers,
  buildSessionThread,
  readMeasures,
  type ChatFacts,
  type Reply,
  type ThreadItem,
} from "@/features/sessions/chat/chat-thread-model";
import { previousMluOf } from "@/features/sessions/chat/use-previous-mlu";
import type { FeatureSignal, TranscriptLine } from "@/lib/workflow";

function line(lineId: string, speaker: string, text = "words here"): TranscriptLine {
  return { lineId, speaker, text };
}

function signal(featureName: string, rawValue: FeatureSignal["rawValue"]): FeatureSignal {
  return {
    featureName,
    displayName: featureName,
    description: "",
    valueType: "float",
    unit: "",
    value: String(rawValue),
    rawValue,
    calculationMethod: "",
    requiredInputs: [],
    limitations: [],
    clinicalInterpretationCaution: "",
    interpretationHint: "",
    referenceText: "",
  };
}

type FactOverrides = {
  [Key in keyof ChatFacts]?: ChatFacts[Key] extends object | null ? Partial<NonNullable<ChatFacts[Key]>> | null : ChatFacts[Key];
};

function facts(overrides: FactOverrides = {}): ChatFacts {
  const base: ChatFacts = {
    loading: false,
    loadFailed: false,
    consentGranted: true,
    source: "recording",
    audio: { step: "idle", durationSeconds: null, unavailable: false },
    transcript: { ready: false, lines: [], saveStatus: "idle", fromFile: false },
    analysis: { status: "not_started", extracted: false, signals: [], previousMlu: null },
    report: { status: "not_started", saveStatus: "idle" },
    assignment: null,
  };
  return {
    ...base,
    ...overrides,
    audio: { ...base.audio, ...overrides.audio },
    transcript: { ...base.transcript, ...overrides.transcript },
    analysis: { ...base.analysis, ...overrides.analysis },
    report: { ...base.report, ...overrides.report },
    assignment: overrides.assignment === undefined ? base.assignment : (overrides.assignment as ChatFacts["assignment"]),
  } as ChatFacts;
}

const kinds = (items: ThreadItem[]) => items.map((item) => item.kind);
const actions = (replies: Reply[]) => replies.map((reply) => reply.action);

function repliesOf(items: ThreadItem[], kind: ThreadItem["kind"]): Reply[] {
  const item = items.find((candidate) => candidate.kind === kind);
  if (!item || !("replies" in item)) throw new Error(`no ${kind} item with replies`);
  return item.replies;
}

const mixed = [line("1", "THER"), line("2", "CHI"), line("3", "UNK"), line("4", "CHI"), line("5", "")];
const complete = [line("1", "THER"), line("2", "CHI"), line("3", "THER"), line("4", "CHI")];

describe("session conversation", () => {
  it("shows only a loading line until the session has been read", () => {
    const thread = buildSessionThread(facts({ loading: true }));
    expect(kinds(thread.items)).toEqual(["loading"]);
  });

  it("says so when the session cannot be read, and offers nothing else", () => {
    expect(kinds(buildSessionThread(facts({ loadFailed: true })).items)).toEqual(["load-failed"]);
  });

  it("collects no audio while the case's consent is not active", () => {
    const thread = buildSessionThread(facts({ consentGranted: false }));
    expect(kinds(thread.items)).toEqual(["consent-inactive"]);
    expect(thread.step).toBe("audio");
  });

  it("asks for audio first, by the route the therapist chose", () => {
    const thread = buildSessionThread(facts({ source: "audio" }));
    expect(thread.items).toEqual([{ id: "ask-audio", role: "assistant", kind: "ask-audio", source: "audio" }]);
    expect(thread.step).toBe("audio");
    expect(thread.completed).toEqual({ audio: false, transcript: false, measures: false, report: false });
  });

  it("asks before audio is sent, with sending as the one primary reply", () => {
    const thread = buildSessionThread(facts({ audio: { step: "confirm", durationSeconds: 728 } }));
    expect(kinds(thread.items)).toEqual(["audio", "confirm-upload"]);
    expect(thread.items[0]).toMatchObject({ role: "user", durationSeconds: 728 });
    expect(repliesOf(thread.items, "confirm-upload")).toEqual([
      { action: "upload-audio", primary: true },
      { action: "discard-audio" },
    ]);
  });

  it.each(["uploading", "polling", "done"] as const)("shows work in progress while the audio is %s", (step) => {
    const thread = buildSessionThread(facts({ audio: { step } }));
    expect(kinds(thread.items)).toEqual(["audio", "transcribing"]);
    expect(thread.items[1]).toMatchObject({ uploading: step === "uploading" });
  });

  it("reports a failed transcription without any stand-in transcript", () => {
    const thread = buildSessionThread(facts({ audio: { step: "error", unavailable: true } }));
    expect(kinds(thread.items)).toEqual(["audio", "transcription-failed"]);
    expect(thread.items[1]).toMatchObject({ unavailable: true });
    expect(actions(repliesOf(thread.items, "transcription-failed"))).toEqual(["retry-audio"]);
    expect(thread.completed.audio).toBe(false);
  });

  it("offers to set the remaining speakers when only some lines are unknown", () => {
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: mixed, saveStatus: "saved" } }));
    const ready = thread.items.find((item) => item.kind === "transcript-ready");
    expect(ready).toMatchObject({ lineCount: 5, unknownCount: 2 });
    expect(actions(repliesOf(thread.items, "transcript-ready"))).toEqual([
      "assign-therapist",
      "assign-child",
      "open-transcript",
    ]);
    expect(thread.step).toBe("transcript");
    expect(kinds(thread.items)).not.toContain("speakers-complete");
  });

  it("sends the therapist to the transcript when no line has a speaker at all", () => {
    // A hosted transcription returns every line as unknown. "Set the rest" has
    // nothing to be the rest of, and would label the whole session as one person.
    const allUnknown = [line("1", "UNK"), line("2", "UNK"), line("3", "")];
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: allUnknown, saveStatus: "saved" } }));
    expect(repliesOf(thread.items, "transcript-ready")).toEqual([{ action: "open-transcript", primary: true }]);
  });

  it("previews the child's first line and the first line without a speaker", () => {
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: mixed, saveStatus: "saved" } }));
    const ready = thread.items.find((item) => item.kind === "transcript-ready");
    if (ready?.kind !== "transcript-ready") throw new Error("no transcript-ready item");
    expect(ready.preview.map((preview) => [preview.lineId, preview.speaker])).toEqual([
      ["2", "child"],
      ["3", "unknown"],
    ]);
  });

  it("offers the measures once every line has a speaker", () => {
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: complete, saveStatus: "saved" } }));
    expect(repliesOf(thread.items, "transcript-ready")).toEqual([]);
    expect(repliesOf(thread.items, "speakers-complete")).toEqual([
      { action: "extract-measures", primary: true, blocked: undefined },
      { action: "open-transcript" },
    ]);
    expect(thread.step).toBe("measures");
  });

  it("echoes this visit's set-all choice as what the therapist said", () => {
    const thread = buildSessionThread(
      facts({
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        assignment: { speaker: "THER", count: 3 },
      }),
    );
    expect(thread.items.find((item) => item.kind === "action")).toMatchObject({
      role: "user",
      action: "assigned-therapist",
      count: 3,
    });
    expect(thread.items.find((item) => item.kind === "speakers-complete")).toMatchObject({ assigned: true });
  });

  it("blocks the measures when no line is the child's", () => {
    const noChild = [line("1", "THER"), line("2", "THER")];
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: noChild, saveStatus: "saved" } }));
    expect(repliesOf(thread.items, "speakers-complete")[0]).toEqual({
      action: "extract-measures",
      primary: true,
      blocked: "no-child-lines",
    });
  });

  it("blocks the measures until the transcript is saved", () => {
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: complete, saveStatus: "saving" } }));
    expect(repliesOf(thread.items, "speakers-complete")[0].blocked).toBe("unsaved-transcript");
  });

  it("stops at a failed save and offers to save again", () => {
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: complete, saveStatus: "failed" } }));
    expect(kinds(thread.items).at(-1)).toBe("save-failed");
    expect(actions(repliesOf(thread.items, "save-failed"))).toEqual(["retry-save"]);
  });

  it("shows the measures the backend sent and then offers the report", () => {
    const thread = buildSessionThread(
      facts({
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        analysis: {
          status: "completed",
          extracted: true,
          signals: [
            signal("mean_length_of_utterance_words", 2.8),
            signal("total_word_count", 129),
            signal("number_of_different_words", 61),
            signal("child_utterance_count", 46),
          ],
          previousMlu: 2.5,
        },
      }),
    );
    expect(kinds(thread.items)).toEqual(["audio", "transcript-ready", "speakers-complete", "action", "measures"]);
    expect(thread.items.find((item) => item.kind === "measures")).toMatchObject({
      measures: { mlu: 2.8, totalWords: 129, distinctWords: 61, childUtterances: 46, previousMlu: 2.5 },
    });
    expect(actions(repliesOf(thread.items, "measures"))).toEqual(["generate-report", "open-measures", "open-transcript"]);
    // Earlier messages no longer carry the replies that would repeat a finished step.
    expect(repliesOf(thread.items, "speakers-complete")).toEqual([]);
    expect(thread.step).toBe("report");
  });

  it("does not show measures taken from an earlier version of the transcript", () => {
    const thread = buildSessionThread(
      facts({
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        analysis: { status: "stale", extracted: false, signals: [signal("mean_length_of_utterance_words", 2.8)] },
      }),
    );
    expect(kinds(thread.items)).not.toContain("measures");
    expect(actions(repliesOf(thread.items, "measures-stale"))).toEqual(["extract-measures", "open-transcript"]);
  });

  it("never offers two primary replies at once", () => {
    const stages: FactOverrides[] = [
      { audio: { step: "confirm" } },
      { audio: { step: "error" } },
      { transcript: { ready: true, lines: [line("1", "UNK")], saveStatus: "saved" } },
      { transcript: { ready: true, lines: complete, saveStatus: "saved" } },
      { transcript: { ready: true, lines: complete, saveStatus: "failed" } },
      { transcript: { ready: true, lines: complete, saveStatus: "saved" }, analysis: { status: "failed" } },
      { transcript: { ready: true, lines: complete, saveStatus: "saved" }, analysis: { status: "stale" } },
      { transcript: { ready: true, lines: complete, saveStatus: "saved" }, analysis: { status: "completed", extracted: true } },
      {
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        analysis: { status: "completed", extracted: true },
        report: { status: "not_started", saveStatus: "failed" },
      },
      {
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        analysis: { status: "completed", extracted: true },
        report: { status: "stale", saveStatus: "idle" },
      },
      {
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        analysis: { status: "completed", extracted: true },
        report: { status: "draft", saveStatus: "saved" },
      },
    ];
    for (const stage of stages) {
      const primaries = buildSessionThread(facts(stage)).items
        .flatMap((item) => ("replies" in item ? item.replies : []))
        .filter((reply) => reply.primary);
      expect(primaries, JSON.stringify(stage)).toHaveLength(1);
    }
  });

  it("leaves the choice between speakers without a primary reply", () => {
    // Which of the two is right is the therapist's knowledge, so neither is pushed.
    const thread = buildSessionThread(facts({ transcript: { ready: true, lines: mixed, saveStatus: "saved" } }));
    expect(repliesOf(thread.items, "transcript-ready").filter((reply) => reply.primary)).toEqual([]);
  });

  it("ends with the report draft and marks every step complete", () => {
    const thread = buildSessionThread(
      facts({
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        analysis: { status: "completed", extracted: true },
        report: { status: "draft", saveStatus: "saved" },
      }),
    );
    expect(kinds(thread.items).slice(-2)).toEqual(["action", "report-ready"]);
    expect(repliesOf(thread.items, "report-ready")).toEqual([{ action: "open-report", primary: true }]);
    expect(thread.completed).toEqual({ audio: true, transcript: true, measures: true, report: true });
  });

  it("asks for a new draft when the report is older than the transcript or measures", () => {
    const thread = buildSessionThread(
      facts({
        transcript: { ready: true, lines: complete, saveStatus: "saved" },
        analysis: { status: "completed", extracted: true },
        report: { status: "stale", saveStatus: "idle" },
      }),
    );
    expect(actions(repliesOf(thread.items, "report-stale"))).toEqual(["generate-report"]);
    expect(thread.completed.report).toBe(false);
  });

  it("shows a transcript file, not audio, when the transcript was attached", () => {
    const thread = buildSessionThread(
      facts({ transcript: { ready: true, lines: complete, saveStatus: "saved", fromFile: true } }),
    );
    expect(thread.items[0]).toMatchObject({ role: "user", kind: "transcript-file" });
  });
});

describe("measures", () => {
  it("never substitutes a number for a value the backend did not send", () => {
    expect(readMeasures([], null)).toEqual({
      mlu: null,
      totalWords: null,
      distinctWords: null,
      childUtterances: null,
      previousMlu: null,
    });
    expect(readMeasures([signal("mean_length_of_utterance_words", null), signal("total_word_count", "n/a")], null)).toMatchObject({
      mlu: null,
      totalWords: null,
    });
  });

  it("reads a measure under any of the names the extractors use", () => {
    expect(readMeasures([signal("mluw", 3.1), signal("ndw", 40)], null)).toMatchObject({ mlu: 3.1, distinctWords: 40 });
  });

  it("takes the previous session's MLU from the point before this session", () => {
    const trends = {
      features: [],
      cases: [
        {
          case_id: "case-1",
          case_label: "C-1",
          points: [
            { session_id: "s1", session_date: "2026-09-01", values: { mlu_words: 2.5 } },
            { session_id: "s2", session_date: "2026-10-01", values: { mlu_words: 2.8 } },
          ],
        },
      ],
    };
    expect(previousMluOf(trends, "s2")).toBe(2.5);
    // The first session has nothing before it, and an unknown session has no place in the series.
    expect(previousMluOf(trends, "s1")).toBeNull();
    expect(previousMluOf(trends, "s9")).toBeNull();
  });
});

describe("assigning speakers", () => {
  it("sets only the lines without a speaker", () => {
    expect(assignUnknownSpeakers(mixed, "THER").map((item) => item.speaker)).toEqual(["THER", "CHI", "THER", "CHI", "THER"]);
  });
});
