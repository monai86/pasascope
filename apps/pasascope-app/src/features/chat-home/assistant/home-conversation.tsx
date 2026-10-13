"use client";

import Link from "next/link";
import { Fragment, useEffect, useRef, useState } from "react";

import {
  AssistantMessage,
  ChatCard,
  ChatError,
  ChatNote,
  ChatThread,
  QuickReplies,
  QuickReply,
  UserBubble,
} from "@/components/chat-shell/chat-primitives";
import { assistantMessages, type AskTopic } from "@/features/chat-home/assistant/assistant.messages";
import {
  buildReply,
  localIsoDate,
  type HomeTurn,
  type ReplyAction,
  type StartKind,
} from "@/features/chat-home/assistant/replies";
import { chatHomeMessages } from "@/features/chat-home/chat-home.messages";
import type { HomeSessionTone } from "@/features/chat-home/chat-home-model";
import type { ChatHomeState } from "@/features/chat-home/use-chat-home";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";

export { interpret } from "@/features/chat-home/assistant/interpret";
export type { HomeTurn } from "@/features/chat-home/assistant/replies";

// Long enough to read as a reply, short enough not to be waited for.
const ANSWER_DELAY_MS = 420;
const ROW =
  "flex min-h-[52px] items-center justify-between gap-3 border-t border-chat-line px-4 py-2.5 text-ink transition first:border-t-0 hover:bg-chat-frame focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none";
const DOT: Record<HomeSessionTone, string> = {
  action: "bg-navy",
  progress: "bg-tint-strong",
  attention: "bg-[color:var(--color-warning-border)]",
};
const LINK_HREF = { cases: "/cases", reports: "/reports", privacy: "/privacy", settings: "/settings" } as const;

type Handlers = {
  onAsk: (topic: AskTopic, label: string) => void;
  onStart: (start: StartKind) => void;
  onSearch: (text: string) => void;
};

/**
 * Questions typed on the chat home and their prepared answers. Nothing here is
 * stored or sent anywhere: the thread lives on this screen and is gone on reload.
 */
export function HomeConversation({
  turns,
  home,
  onClear,
  ...handlers
}: Handlers & { turns: HomeTurn[]; home: ChatHomeState; onClear: () => void }) {
  const t = useMessages(assistantMessages);
  const end = useRef<HTMLDivElement>(null);
  const today = localIsoDate();

  function showLatest() {
    end.current?.scrollIntoView?.({ block: "end", behavior: "smooth" });
  }

  useEffect(showLatest, [turns.length]);

  return (
    <ChatThread label={t.threadLabel} heading={t.threadLabel} className="flex-1 pb-6">
      {turns.map((turn, index) => (
        <Fragment key={turn.id}>
          <UserBubble testId="home-question">{turn.said}</UserBubble>
          <Answer
            turn={turn}
            home={home}
            today={today}
            onShown={showLatest}
            onClear={index === turns.length - 1 ? onClear : undefined}
            {...handlers}
          />
        </Fragment>
      ))}
      {/* The margin clears the composer, which stays over the foot of the page. */}
      <div ref={end} aria-hidden="true" className="scroll-mb-48" />
    </ChatThread>
  );
}

function Answer({
  turn,
  home,
  today,
  onShown,
  onClear,
  onAsk,
  onStart,
  onSearch,
}: Handlers & { turn: HomeTurn; home: ChatHomeState; today: string; onShown: () => void; onClear?: () => void }) {
  const t = useMessages(assistantMessages);
  const h = useMessages(chatHomeMessages);
  const { locale, setLocale } = useLocale();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setShown(true), ANSWER_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (shown) onShown();
    // Only the moment the answer appears matters here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shown]);

  if (!shown) {
    return (
      <div role="status" className="chat-rise flex h-10 w-[68px] items-center justify-center gap-1.5 rounded-full bg-surface shadow-chat-card">
        <span className="sr-only">{t.typing}</span>
        <span aria-hidden="true" className="chat-typing-dot" />
        <span aria-hidden="true" className="chat-typing-dot" />
        <span aria-hidden="true" className="chat-typing-dot" />
      </div>
    );
  }

  const reply = buildReply(turn, t, home, today);
  const [first, ...rest] = reply.lines;

  function label(action: ReplyAction): string {
    switch (action.kind) {
      case "ask":
        return t.ask[action.topic];
      case "start":
        return h.start.intents[action.start];
      case "link":
        return t.links[action.to];
      case "locale":
        return t.languages[action.locale];
      case "search":
        return t.searchFor(action.text);
      case "retry":
        return t.retry;
    }
  }

  function press(action: ReplyAction) {
    switch (action.kind) {
      case "ask":
        return onAsk(action.topic, t.ask[action.topic]);
      case "start":
        return onStart(action.start);
      case "locale":
        return setLocale(action.locale);
      case "search":
        return onSearch(action.text);
      case "retry":
        return home.status === "error" ? home.retry() : undefined;
      case "link":
        return undefined;
    }
  }

  // The one button that begins work or opens a page leads; questions stay quiet.
  const leading = reply.actions.findIndex((action) => action.kind === "start" || action.kind === "link" || action.kind === "retry");

  return (
    <AssistantMessage testId="home-answer">
      {turn.understoodAs ? <ChatNote>{t.understoodAs(turn.understoodAs)}</ChatNote> : null}
      {reply.status === "failed" ? <ChatError>{first}</ChatError> : <p>{first}</p>}

      {reply.steps.length > 0 ? (
        <ol className="flex flex-col gap-2.5">
          {reply.steps.map((step, index) => (
            <li key={step} className="chat-rise flex gap-3" style={{ animationDelay: `${index * 45}ms` }}>
              <span
                aria-hidden="true"
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-surface text-[13px] font-semibold text-ink shadow-chat-card"
              >
                {index + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      ) : null}

      {reply.sessions.length > 0 ? (
        <ChatCard>
          <ul>
            {reply.sessions.map((row) => (
              <li key={row.sessionId} className="border-t border-chat-line first:border-t-0">
                <Link href={row.href} className={cn(ROW, "border-t-0")}>
                  <span className="flex min-w-0 flex-col leading-snug">
                    <span className="truncate font-semibold">{row.caseLabel}</span>
                    <span className="flex items-center gap-2 text-[13px] text-ink-subtle">
                      <span aria-hidden="true" className={cn("h-2 w-2 shrink-0 rounded-full", DOT[row.tone])} />
                      <span className="truncate">{h.stage[row.stage]}</span>
                    </span>
                  </span>
                  <span className="shrink-0 text-[13px] text-ink-subtle">
                    {formatDate(row.sessionDate, locale, { day: "numeric", month: "short" })}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </ChatCard>
      ) : null}

      {reply.cases.length > 0 ? (
        <ChatCard>
          <ul>
            {reply.cases.map((row) => (
              <li key={row.caseId} className="border-t border-chat-line first:border-t-0">
                <Link href={row.href} className={cn(ROW, "border-t-0")}>
                  <span className="truncate font-semibold">{row.label}</span>
                  {row.code !== row.label ? <span className="shrink-0 text-[13px] text-ink-subtle">{row.code}</span> : null}
                </Link>
              </li>
            ))}
          </ul>
        </ChatCard>
      ) : null}

      {rest.map((line) => (
        <p key={line} className={reply.steps.length + reply.sessions.length + reply.cases.length > 0 ? "text-ink-muted" : undefined}>
          {line}
        </p>
      ))}

      {reply.actions.length > 0 || onClear ? (
        <QuickReplies>
          {reply.actions.map((action, index) => {
            const text = label(action);
            return action.kind === "link" ? (
              <QuickReply key={text} href={LINK_HREF[action.to]} primary={index === leading}>
                {text}
              </QuickReply>
            ) : (
              <QuickReply key={text} primary={index === leading} onClick={() => press(action)}>
                {text}
              </QuickReply>
            );
          })}
          {onClear ? (
            <button
              type="button"
              onClick={onClear}
              className="min-h-11 rounded-full px-3 text-sm font-medium text-ink-subtle underline-offset-4 hover:text-ink hover:underline focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
            >
              {t.clear}
            </button>
          ) : null}
        </QuickReplies>
      ) : null}
    </AssistantMessage>
  );
}
