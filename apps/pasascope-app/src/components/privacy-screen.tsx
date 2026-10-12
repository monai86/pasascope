"use client";

import { LanguageToggle } from "@/components/language-toggle";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { privacyMessages } from "@/components/privacy.messages";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";

const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL?.trim() ?? "";

/** Public page, readable without signing in: what is stored, where it goes, how to remove it. */
export function PrivacyScreen() {
  const t = useMessages(privacyMessages);
  const safety = useSafetyCopy();

  return (
    <main className="app-canvas flex min-h-dvh flex-col gap-6 p-4 text-ink sm:p-6 lg:p-8">
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3">
        <PasaScopeLogo size="sm" showSubtitle={false} />
        <LanguageToggle />
      </header>

      <Card className="mx-auto w-full max-w-3xl p-6 sm:p-8">
        <h1 className="text-3xl font-semibold leading-tight">{t.title}</h1>
        <p className="mt-3 text-base leading-7 text-ink-muted">{t.intro}</p>
        <p className="mt-3 text-sm font-semibold text-brand">{safety.SAFETY_NOTICE_DEFAULT}</p>

        {t.sections.map((section) => (
          <section key={section.title} className="mt-7">
            <h2 className="text-lg font-semibold">{section.title}</h2>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-6" role="list">
              {section.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ))}

        <section className="mt-7">
          <h2 className="text-lg font-semibold">{t.contactTitle}</h2>
          <p className="mt-2 text-sm leading-6">
            {CONTACT_EMAIL ? t.contactWithEmail(CONTACT_EMAIL) : t.contactWithoutEmail}
          </p>
        </section>

        <div className="mt-8">
          <Button href="/login" variant="secondary">{t.backToSignIn}</Button>
        </div>
      </Card>
    </main>
  );
}
