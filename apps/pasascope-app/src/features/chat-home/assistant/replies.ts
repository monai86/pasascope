import type { AskTopic, FixedTopic, assistantMessages } from "@/features/chat-home/assistant/assistant.messages";
import type { AssistantIntent } from "@/features/chat-home/assistant/interpret";
import { caseCode, caseLabel, type HomeSessionRow } from "@/features/chat-home/chat-home-model";
import type { ChatHomeState } from "@/features/chat-home/use-chat-home";
import type { Locale } from "@/i18n/config";

type Copy = (typeof assistantMessages)["en"];

/** One question on the chat home and the topic it was read as. */
export type HomeTurn = {
  id: number;
  said: string;
  topic: ConversationTopic | "unknown";
  understoodAs?: string;
};

/** Topics answered in the conversation; the rest open the start-session conversation. */
export type ConversationTopic = Exclude<AssistantIntent, "record" | "upload" | "newSession" | "findCase" | "newCase">;

export type StartKind = "recording" | "audio" | "findCase" | "newSession";

/** A button under an answer. None of them changes a record: they ask, open a page or begin the guided start. */
export type ReplyAction =
  | { kind: "ask"; topic: AskTopic }
  | { kind: "start"; start: StartKind }
  | { kind: "link"; to: "cases" | "reports" | "privacy" | "settings" }
  | { kind: "locale"; locale: Locale }
  | { kind: "search"; text: string }
  | { kind: "retry" };

export type CaseRow = { caseId: string; label: string; code: string; href: string };

export type AssistantReply = {
  /** "loading" and "failed" stand in for an answer that needs the caller's sessions and cases. */
  status: "ready" | "loading" | "failed";
  lines: string[];
  steps: string[];
  /** Shown between the first line and the rest, like `steps`. */
  sessions: HomeSessionRow[];
  cases: CaseRow[];
  actions: ReplyAction[];
};

const ROWS_SHOWN = 6;
// A longer line is a sentence, not a case's name.
const NAME_LENGTH_MAX = 30;

const FIXED_ACTIONS: Record<FixedTopic, ReplyAction[]> = {
  greeting: [{ kind: "ask", topic: "capabilities" }, { kind: "ask", topic: "howto" }, { kind: "ask", topic: "today" }],
  capabilities: [
    { kind: "start", start: "recording" },
    { kind: "start", start: "audio" },
    { kind: "ask", topic: "howto" },
    { kind: "ask", topic: "today" },
  ],
  howto: [{ kind: "start", start: "recording" }, { kind: "start", start: "audio" }, { kind: "start", start: "findCase" }],
  transcript: [{ kind: "ask", topic: "speakers" }, { kind: "ask", topic: "formats" }],
  speakers: [{ kind: "ask", topic: "measures" }, { kind: "ask", topic: "pending" }],
  measures: [{ kind: "ask", topic: "diagnosis" }, { kind: "ask", topic: "reports" }],
  formats: [{ kind: "start", start: "audio" }, { kind: "ask", topic: "privacy" }],
  privacy: [{ kind: "link", to: "privacy" }],
  consent: [{ kind: "link", to: "cases" }, { kind: "ask", topic: "privacy" }],
  delete: [{ kind: "link", to: "cases" }, { kind: "ask", topic: "privacy" }],
  diagnosis: [{ kind: "ask", topic: "measures" }],
  language: [{ kind: "locale", locale: "th" }, { kind: "locale", locale: "en" }],
  settings: [{ kind: "link", to: "settings" }],
  identity: [{ kind: "ask", topic: "capabilities" }],
  thanks: [],
  bye: [],
};

const EMPTY: AssistantReply = { status: "ready", lines: [], steps: [], sessions: [], cases: [], actions: [] };

/** Today's date as the browser's calendar has it, in the form session dates use. */
export function localIsoDate(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/**
 * The answer to one turn. It is worked out again on every render, so it follows
 * the interface language and the latest sessions and cases.
 */
export function buildReply(turn: HomeTurn, t: Copy, home: ChatHomeState, today: string): AssistantReply {
  const { topic } = turn;

  if (topic === "unknown") {
    return {
      ...EMPTY,
      lines: t.unknown.lines,
      actions: [
        { kind: "ask", topic: "capabilities" },
        { kind: "ask", topic: "howto" },
        { kind: "ask", topic: "today" },
        ...(turn.said.length <= NAME_LENGTH_MAX ? [{ kind: "search", text: turn.said } as const] : []),
      ],
    };
  }

  if (topic !== "today" && topic !== "pending" && topic !== "cases" && topic !== "reports") {
    const fixed = t.fixed[topic];
    return { ...EMPTY, lines: fixed.lines, steps: fixed.steps ?? [], actions: FIXED_ACTIONS[topic] };
  }

  if (home.status === "loading") return { ...EMPTY, status: "loading", lines: [t.loading] };
  if (home.status === "error") return { ...EMPTY, status: "failed", lines: [t.failed], actions: [{ kind: "retry" }] };

  const rows = home.model.rows;
  const unfinished = rows.filter((row) => row.stage !== "report");

  if (topic === "today") {
    const dated = rows.filter((row) => row.sessionDate.slice(0, 10) === today);
    const earlier = unfinished.filter((row) => !dated.includes(row));
    return {
      ...EMPTY,
      lines: [
        dated.length > 0 ? t.today.some(dated.length) : t.today.none,
        ...(earlier.length > 0 ? [t.today.pendingToo(earlier.length)] : []),
        t.today.noSchedule,
      ],
      sessions: dated.slice(0, ROWS_SHOWN),
      actions: [
        { kind: "start", start: "newSession" },
        ...(earlier.length > 0 ? [{ kind: "ask", topic: "pending" } as const] : []),
        { kind: "ask", topic: "cases" },
      ],
    };
  }

  if (topic === "pending") {
    return {
      ...EMPTY,
      lines: [
        unfinished.length > 0 ? t.pending.some(unfinished.length) : rows.length > 0 ? t.pending.none : t.pending.noSessions,
      ],
      sessions: unfinished.slice(0, ROWS_SHOWN),
      actions: [{ kind: "start", start: "newSession" }],
    };
  }

  if (topic === "reports") {
    const drafted = rows.filter((row) => row.stage === "report");
    return {
      ...EMPTY,
      lines: [drafted.length > 0 ? t.reports.ready(drafted.length) : t.reports.none, t.reports.about],
      sessions: drafted.slice(0, ROWS_SHOWN),
      actions: [{ kind: "link", to: "reports" }],
    };
  }

  const cases = home.cases;
  return {
    ...EMPTY,
    lines: [
      cases.length > 0 ? t.cases.some(cases.length) : t.cases.none,
      ...(cases.length > ROWS_SHOWN ? [t.cases.more(cases.length - ROWS_SHOWN)] : []),
    ],
    cases: cases.slice(0, ROWS_SHOWN).map((caseItem) => ({
      caseId: caseItem.case_id,
      label: caseLabel(caseItem),
      code: caseCode(caseItem),
      href: `/cases/${encodeURIComponent(caseItem.case_id)}`,
    })),
    actions: [{ kind: "link", to: "cases" }, { kind: "start", start: "findCase" }],
  };
}
