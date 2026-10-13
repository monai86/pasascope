"use client";

import Link from "next/link";
import { useState } from "react";
import { Search } from "lucide-react";

import { chatHomeMessages } from "@/features/chat-home/chat-home.messages";
import { filterSessionRows, type HomeSessionTone } from "@/features/chat-home/chat-home-model";
import type { ChatHomeState } from "@/features/chat-home/use-chat-home";
import { SkeletonLine } from "@/components/skeleton";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";

const DOT: Record<HomeSessionTone, string> = {
  action: "bg-navy",
  progress: "bg-tint-strong",
  attention: "bg-[color:var(--color-warning-border)]",
};

/** The side panel of the chat home: the caller's latest sessions and where each stands. */
export function RecentSessionsPanel({ home, onNewSession }: { home: ChatHomeState; onNewSession: () => void }) {
  const t = useMessages(chatHomeMessages).recent;
  const stage = useMessages(chatHomeMessages).stage;
  const { locale } = useLocale();
  const [query, setQuery] = useState("");
  const rows = home.status === "ready" ? filterSessionRows(home.model.rows, query) : [];

  return (
    <section aria-labelledby="recent-sessions-title" className="flex min-h-0 flex-1 flex-col">
      <h2 id="recent-sessions-title" className="font-display text-[22px] font-semibold leading-snug text-ink">
        {t.title}
      </h2>

      <div className="mb-1 mt-4 flex min-h-11 items-center gap-2.5 rounded-full border border-chat-line px-4 text-ink-subtle focus-within:ring-4 focus-within:ring-[color:var(--color-focus-ring)]">
        <Search size={18} aria-hidden="true" className="shrink-0" />
        <input
          type="search"
          aria-label={t.searchLabel}
          placeholder={t.searchPlaceholder}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-h-11 min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-ink-subtle focus-visible:outline-none"
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {home.status === "loading" ? (
          <div role="status" className="space-y-4 py-4">
            <span className="sr-only">{t.loading}</span>
            <SkeletonLine className="w-2/3" />
            <SkeletonLine className="w-1/2" />
            <SkeletonLine className="w-3/5" />
          </div>
        ) : null}

        {home.status === "error" ? (
          <div role="alert" className="space-y-3 py-4">
            <p className="text-sm text-ink-muted">{t.failed}</p>
            <Button variant="secondary" onClick={home.retry}>{t.retry}</Button>
          </div>
        ) : null}

        {home.status === "ready" && rows.length === 0 ? (
          <p className="py-4 text-sm leading-6 text-ink-subtle">
            {home.model.rows.length === 0 ? t.empty : t.noMatch}
          </p>
        ) : null}

        {rows.length > 0 ? (
          <ul>
            {rows.map((row, index) => (
              <li
                key={row.sessionId}
                className="chat-rise border-b border-chat-line"
                style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
              >
                <Link
                  href={row.href}
                  className="flex flex-col gap-1.5 rounded-control py-4 leading-normal text-ink transition hover:bg-chat-frame focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
                >
                  <span className="font-semibold">{row.caseLabel}</span>
                  <span className="flex items-center justify-between gap-2 text-[13px] text-ink-subtle">
                    <span className="flex min-w-0 items-center gap-2">
                      <span aria-hidden="true" className={cn("h-2 w-2 shrink-0 rounded-full", DOT[row.tone])} />
                      <span className="truncate">{stage[row.stage]}</span>
                    </span>
                    <span className="shrink-0">
                      {formatDate(row.sessionDate, locale, { day: "numeric", month: "short" })}
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <Button onClick={onNewSession} className="mt-4 w-full">
        {t.newSession}
      </Button>
    </section>
  );
}
