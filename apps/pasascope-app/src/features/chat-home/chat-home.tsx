"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Clock, FolderOpen, History, Mic, Upload } from "lucide-react";

import { ChatComposer } from "@/components/chat-shell/chat-composer";
import {
  AssistantMessage,
  ChatComposerDock,
  ChatError,
  ChatThread,
  QuickReplies,
  QuickReply,
} from "@/components/chat-shell/chat-primitives";
import { ChatShellPanel } from "@/components/chat-shell/chat-shell-context";
import { PasaScopeLogoMark } from "@/components/pasascope-logo";
import { SkeletonLine } from "@/components/skeleton";
import { chatHomeMessages } from "@/features/chat-home/chat-home.messages";
import { RecentSessionsPanel } from "@/features/chat-home/recent-sessions-panel";
import { StartSessionThread, type StartOpener } from "@/features/chat-home/start-session-thread";
import { useChatHome } from "@/features/chat-home/use-chat-home";
import { useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";

const AUDIO_TYPES = "audio/*,.wav,.mp3,.m4a,.webm,.ogg,.flac";
const CARD =
  "flex min-h-[68px] items-center gap-3.5 border-t border-chat-line px-4 py-2.5 text-left text-ink transition first:border-t-0 hover:bg-chat-frame focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none md:flex-1 md:basis-[180px] md:flex-col md:items-start md:gap-9 md:rounded-[18px] md:border-t-0 md:bg-surface md:p-4 md:shadow-chat-card md:hover:bg-surface md:hover:shadow-soft md:focus-visible:ring-offset-0";

/**
 * The chat shell's home: one question, three ways to answer it, and a field
 * that finds a case. Starting anything opens a short conversation in place of
 * the greeting; the latest sessions sit in the side panel.
 */
export function ChatHome() {
  const t = useMessages(chatHomeMessages);
  const home = useChatHome();
  const [opener, setOpener] = useState<StartOpener | null>(null);
  // Remounts the conversation when a new one starts while another is open.
  const [threadKey, setThreadKey] = useState(0);
  const [text, setText] = useState("");
  // Typing finds a case, so the field is live on the greeting and while a case
  // is being chosen, and inert for the rest of the start conversation.
  const [choosingCase, setChoosingCase] = useState(true);

  function start(next: StartOpener) {
    setOpener(next);
    setThreadKey((current) => current + 1);
    setText("");
    setChoosingCase(true);
  }

  function reset() {
    setOpener(null);
    setText("");
    setChoosingCase(true);
  }

  const resume = home.status === "ready" ? home.model.resume : null;

  return (
    <div className="flex flex-1 flex-col">
      <ChatShellPanel triggerLabel={t.recent.trigger} triggerIcon={History}>
        <RecentSessionsPanel home={home} onNewSession={() => start({ kind: "newSession" })} />
      </ChatShellPanel>

      {opener ? (
        home.status === "ready" ? (
          <StartSessionThread
            key={threadKey}
            opener={opener}
            cases={home.cases}
            filter={text}
            onChoosingCaseChange={setChoosingCase}
            onCaseCreated={home.reload}
            onStartOver={reset}
          />
        ) : (
          <ChatThread label={t.threadLabel} heading={t.threadLabel} className="flex-1 pb-6">
            <AssistantMessage>
              {home.status === "error" ? (
                <>
                  <ChatError>{t.recent.failed}</ChatError>
                  <QuickReplies>
                    <QuickReply primary onClick={home.retry}>{t.recent.retry}</QuickReply>
                  </QuickReplies>
                </>
              ) : (
                <div role="status" className="space-y-3">
                  <span className="sr-only">{t.recent.loading}</span>
                  <SkeletonLine className="w-2/3" />
                  <SkeletonLine className="w-1/2" />
                </div>
              )}
            </AssistantMessage>
          </ChatThread>
        )
      ) : (
        <div className="mx-auto flex w-full max-w-[660px] flex-1 flex-col justify-center gap-7 py-4 md:gap-11">
          <div className="flex flex-col items-center text-center">
            <div aria-hidden="true" className="chat-mark-glow grid h-[130px] w-[200px] place-items-center md:h-[150px] md:w-[220px]">
              <PasaScopeLogoMark size="xl" />
            </div>
            <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-ink md:mt-3 md:text-[2.875rem]">
              {t.greeting}
            </h1>
            <p className="mt-1.5 max-w-[280px] text-ink-subtle md:mt-2.5 md:max-w-none">{t.lead}</p>
          </div>

          <div className="flex flex-col overflow-hidden rounded-card bg-surface shadow-chat-card md:flex-row md:flex-wrap md:gap-3.5 md:overflow-visible md:rounded-none md:bg-transparent md:shadow-none">
            <HomeCard
              icon={Mic}
              iconClass="text-highlight"
              title={t.cards.record.title}
              body={t.cards.record.body}
              onClick={() => start({ kind: "recording" })}
              testId="home-card-record"
            />
            <HomeCard
              icon={Upload}
              iconClass="text-tint-strong"
              title={t.cards.upload.title}
              body={t.cards.upload.body}
              onClick={() => start({ kind: "audio" })}
              testId="home-card-upload"
            />
            <HomeCard
              icon={Clock}
              iconClass="text-ink"
              title={t.cards.resume.title}
              body={
                home.status === "loading"
                  ? t.recent.loading
                  : resume
                    ? `${resume.caseLabel} · ${t.stage[resume.stage]}`
                    : t.cards.resume.none
              }
              href={resume?.href}
              testId="home-card-resume"
            />
          </div>
        </div>
      )}

      <ChatComposerDock>
        <ChatComposer
          testId="home-composer"
          label={t.composer.label}
          placeholder={t.composer.placeholder}
          submitLabel={t.composer.submit}
          value={text}
          onChange={setText}
          disabled={Boolean(opener) && !choosingCase}
          onSubmit={() => {
            // While a case is being chosen the text already narrows the list.
            if (!opener) start({ kind: "search", text: text.trim() });
          }}
          attach={{ label: t.composer.attach, accept: AUDIO_TYPES, onFile: (file) => start({ kind: "file", file }) }}
          chips={[{ label: t.composer.chooseCase, icon: FolderOpen, onClick: () => start({ kind: "findCase" }) }]}
        />
      </ChatComposerDock>
    </div>
  );
}

function HomeCard({
  icon: Icon,
  iconClass,
  title,
  body,
  onClick,
  href,
  testId,
}: {
  icon: LucideIcon;
  iconClass: string;
  title: string;
  body: string;
  onClick?: () => void;
  /** A card that goes somewhere; without it and without `onClick` the card is plain text. */
  href?: string;
  testId: string;
}) {
  const content: ReactNode = (
    <>
      <Icon size={26} strokeWidth={1.8} aria-hidden="true" className={cn("shrink-0", iconClass)} />
      <span className="flex min-w-0 flex-col leading-snug">
        <span className="font-semibold">{title}</span>
        <span className="text-sm text-ink-subtle">{body}</span>
      </span>
    </>
  );

  if (href) {
    return <Link href={href} data-testid={testId} className={CARD}>{content}</Link>;
  }
  if (onClick) {
    return <button type="button" onClick={onClick} data-testid={testId} className={CARD}>{content}</button>;
  }
  return <div data-testid={testId} className={CARD}>{content}</div>;
}
