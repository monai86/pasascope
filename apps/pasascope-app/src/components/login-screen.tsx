"use client";

import { AudioLines, FileSignature, ListChecks, ShieldCheck } from "lucide-react";

import { LanguageToggle } from "@/components/language-toggle";
import { loginMessages } from "@/components/login.messages";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useMessages } from "@/i18n/locale-provider";
import { APP_VERSION } from "@/lib/app-version";
import { useSafetyCopy } from "@/lib/safety-copy";

const stepIcons = [AudioLines, ListChecks, FileSignature];

/**
 * The sign-in page: what the product does on the left, the sign-in form on the
 * right. It describes the workflow in plain terms and states the
 * non-diagnostic boundary before anyone signs in.
 */
export function LoginScreen() {
  const t = useMessages(loginMessages);
  const safety = useSafetyCopy();

  return (
    <main className="app-canvas flex min-h-dvh flex-col gap-6 p-4 text-ink sm:p-6 lg:p-8">
      <header className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <PasaScopeLogo size="sm" showSubtitle={false} />
          <span className="hidden text-sm font-medium text-ink-muted sm:inline">{t.productLine}</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="neutral" className="hidden sm:inline-flex">{t.prototypeChip}</Badge>
          <LanguageToggle />
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-6xl flex-1 items-start gap-6 lg:grid-cols-[1.05fr_1fr] lg:items-stretch">
        <Card variant="hero" className="flex flex-col justify-between gap-8 p-6 sm:p-8">
          <div>
            <p className="text-sm font-semibold">{t.hero.eyebrow}</p>
            <h1 className="mt-3 text-3xl font-semibold leading-tight sm:text-4xl">{t.hero.title}</h1>
            <p className="mt-4 max-w-[58ch] text-base leading-7">{t.hero.body}</p>

            <ol className="mt-7 grid gap-3" role="list">
              {t.hero.steps.map((step, index) => {
                const Icon = stepIcons[index] ?? ListChecks;
                return (
                  <li key={step.title} className="flex items-start gap-3 rounded-card bg-navy/20 p-4">
                    <span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-items-center rounded-control bg-surface text-brand">
                      <Icon size={20} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-base font-semibold">
                        {index + 1}. {step.title}
                      </span>
                      <span className="mt-0.5 block text-sm leading-6">{step.body}</span>
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>

          <p className="flex items-start gap-3 border-t border-white/30 pt-5 text-sm leading-6">
            <ShieldCheck size={20} aria-hidden="true" className="mt-0.5 shrink-0" />
            <span>{safety.SAFETY_NOTICE_DEFAULT}</span>
          </p>
        </Card>

        <section className="flex flex-col justify-center">
          <RuntimeLoginPanelClient />
        </section>
      </div>

      <footer className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-2 text-xs text-ink-subtle">
        <p>{t.footer}</p>
        <p>PasaScope {APP_VERSION}</p>
      </footer>
    </main>
  );
}
