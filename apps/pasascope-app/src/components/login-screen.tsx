"use client";

import { FileText, ListChecks, Mic, ShieldCheck } from "lucide-react";

import { LanguageToggle } from "@/components/language-toggle";
import { loginMessages } from "@/components/login.messages";
import { PasaScopeLogo, PasaScopeLogoMark } from "@/components/pasascope-logo";
import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";
import { useMessages } from "@/i18n/locale-provider";
import { APP_VERSION } from "@/lib/app-version";
import { cn } from "@/lib/cn";
import { useSafetyCopy } from "@/lib/safety-copy";

const steps = [
  { icon: Mic, tone: "text-highlight" },
  { icon: ListChecks, tone: "text-tint-strong" },
  { icon: FileText, tone: "text-ink" },
];

/**
 * The sign-in page, drawn like the chat shell it leads to: the same canvas and
 * frame, the mark in its glow, and the workflow as three plain rows beside the
 * form. It states the non-diagnostic boundary before anyone signs in.
 */
export function LoginScreen() {
  const t = useMessages(loginMessages);
  const safety = useSafetyCopy();

  return (
    <main data-shell="chat" className="chat-canvas flex min-h-dvh w-full text-ink md:p-4 xl:p-5">
      <div className="chat-frame flex min-w-0 flex-1 flex-col gap-6 px-4 py-4 md:rounded-shell md:px-8 md:py-6 xl:rounded-chat-frame">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <PasaScopeLogo size="sm" showSubtitle={false} />
            <span className="hidden text-sm text-ink-subtle lg:inline">{t.productLine}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden rounded-full border border-chat-line bg-white/60 px-3 py-1.5 text-xs font-medium text-ink-muted sm:inline-flex">
              {t.prototypeChip}
            </span>
            <LanguageToggle />
          </div>
        </header>

        {/* On a phone the form follows the heading, so signing in needs no scrolling past the steps. */}
        <div className="mx-auto grid w-full max-w-5xl flex-1 content-center items-center gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,440px)] lg:gap-x-12">
          <div className="chat-rise flex flex-col items-center text-center lg:items-start lg:self-end lg:text-left">
            <div aria-hidden="true" className="chat-mark-glow grid h-[110px] w-[170px] place-items-center lg:-ml-9 lg:h-[130px] lg:w-[200px]">
              <PasaScopeLogoMark size="xl" />
            </div>
            <p className="mt-1 text-sm font-medium text-ink-subtle">{t.hero.eyebrow}</p>
            <h1 className="mt-2 font-display text-3xl font-semibold leading-tight text-ink md:text-[2.5rem]">
              {t.hero.title}
            </h1>
            <p className="mt-3 max-w-[46ch] text-ink-muted">{t.hero.body}</p>
          </div>

          <section
            className="chat-rise flex flex-col justify-center lg:col-start-2 lg:row-span-2 lg:row-start-1"
            style={{ animationDelay: "90ms" }}
          >
            <RuntimeLoginPanelClient />
          </section>

          <div
            className="chat-rise flex flex-col items-center gap-4 lg:items-start lg:self-start"
            style={{ animationDelay: "140ms" }}
          >
            <ol role="list" className="w-full max-w-[460px] overflow-hidden rounded-card bg-surface text-left shadow-chat-card">
              {t.hero.steps.map((step, index) => {
                const { icon: Icon, tone } = steps[index] ?? steps[0];
                return (
                  <li key={step.title} className="flex items-center gap-3.5 border-t border-chat-line px-4 py-3 first:border-t-0">
                    <Icon size={24} strokeWidth={1.8} aria-hidden="true" className={cn("shrink-0", tone)} />
                    <span className="flex min-w-0 flex-col leading-snug">
                      <span className="font-semibold">
                        {index + 1}. {step.title}
                      </span>
                      <span className="text-sm text-ink-subtle">{step.body}</span>
                    </span>
                  </li>
                );
              })}
            </ol>

            <p className="flex max-w-[460px] items-start gap-2.5 text-left text-[13px] leading-5 text-ink-subtle">
              <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
              <span>{safety.SAFETY_NOTICE_DEFAULT}</span>
            </p>
          </div>
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-subtle">
          <p>{t.footer}</p>
          <p>PasaScope {APP_VERSION}</p>
        </footer>
      </div>
    </main>
  );
}
