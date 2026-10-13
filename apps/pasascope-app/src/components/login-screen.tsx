"use client";

import type { CSSProperties } from "react";
import { FileText, ListChecks, Mic, ShieldCheck } from "lucide-react";

import { LanguageToggle } from "@/components/language-toggle";
import { loginMessages } from "@/components/login.messages";
import { ChatMarkStage } from "@/components/chat-shell/chat-mark-stage";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";
import { useMessages } from "@/i18n/locale-provider";
import { APP_VERSION } from "@/lib/app-version";
import { useSafetyCopy } from "@/lib/safety-copy";

/** An element's place in the arrival sequence; see `.site-enter` in components.css. */
function enter(step: number): CSSProperties {
  return { "--enter": step } as CSSProperties;
}

const steps = [
  { icon: Mic, tone: "text-highlight" },
  { icon: ListChecks, tone: "text-tint-strong" },
  { icon: FileText, tone: "text-ink" },
];

/**
 * The sign-in page, drawn like the chat shell it leads to: the same canvas and
 * frame, the mark on its tile, and the workflow as one thread running from the
 * recording to the report. Arriving is one short sequence: the mark settles,
 * the heading and its line come into focus, then the thread draws itself. The
 * form fades in with the heading and can be used from the first moment.
 */
export function LoginScreen() {
  const t = useMessages(loginMessages);
  const safety = useSafetyCopy();

  return (
    <main data-shell="chat" className="chat-canvas flex min-h-dvh w-full text-ink md:p-4 xl:p-5">
      <div className="chat-frame flex min-w-0 flex-1 flex-col gap-8 px-4 py-4 md:rounded-shell md:px-8 md:py-6 xl:rounded-chat-frame">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <PasaScopeLogo size="sm" showSubtitle={false} />
            <span className="hidden text-sm text-ink-subtle lg:inline">{t.productLine}</span>
          </div>
          <LanguageToggle />
        </header>

        {/* On a phone the form follows the heading, so signing in needs no scrolling past the steps. */}
        <div className="mx-auto grid w-full max-w-[1080px] flex-1 content-center items-center gap-x-16 gap-y-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,432px)]">
          <div className="flex flex-col items-center text-center lg:items-start lg:self-end lg:text-left">
            <ChatMarkStage className="site-enter-mark lg:-ml-[26px]" />
            <h1 style={enter(1)} className="site-enter login-title mt-5 whitespace-pre-line font-display text-[2rem] font-semibold text-ink md:text-[2.75rem] lg:text-[3rem]">
              {t.hero.title}
            </h1>
            <p style={enter(2)} className="site-enter mt-4 max-w-[44ch] text-lg leading-relaxed text-ink-muted">{t.hero.body}</p>
          </div>

          <section style={enter(1)} className="site-enter-panel mx-auto flex w-full max-w-[480px] flex-col justify-center lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:max-w-none">
            <RuntimeLoginPanelClient />
          </section>

          <div className="flex flex-col items-center gap-6 lg:items-start lg:self-start">
            <ol role="list" className="login-thread w-full max-w-[440px] text-left">
              {t.hero.steps.map((step, index) => {
                const { icon: Icon, tone } = steps[index] ?? steps[0];
                return (
                  <li key={step.title} className="login-thread-step">
                    <span aria-hidden="true" className="login-thread-node">
                      <Icon size={20} strokeWidth={1.8} className={tone} />
                    </span>
                    <span className="flex min-w-0 flex-col pt-1.5 leading-snug">
                      <span className="font-semibold text-ink">{step.title}</span>
                      <span className="mt-0.5 text-[15px] text-ink-muted">{step.body}</span>
                    </span>
                  </li>
                );
              })}
            </ol>

            <p style={enter(11)} className="site-enter flex max-w-[440px] items-start gap-2.5 text-left text-[13px] leading-5 text-ink-muted">
              <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-ink-subtle" />
              <span>{safety.SAFETY_NOTICE_DEFAULT}</span>
            </p>
          </div>
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-muted">
          <p>{t.footer}</p>
          <p>PasaScope {APP_VERSION}</p>
        </footer>
      </div>
    </main>
  );
}
