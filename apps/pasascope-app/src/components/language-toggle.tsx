"use client";

import { startTransition } from "react";
import { useRouter } from "next/navigation";

import { SegmentedControl } from "@/components/ui/segmented-control";
import { shellMessages } from "@/components/shell.messages";
import type { Locale } from "@/i18n/config";
import { useLocale, useMessages } from "@/i18n/locale-provider";

/**
 * Switches the interface between Thai and English. Client components update
 * at once; the refresh re-renders server components with the new cookie.
 */
export function LanguageToggle({ className }: { className?: string }) {
  const router = useRouter();
  const { locale, setLocale } = useLocale();
  const t = useMessages(shellMessages).language;

  function handleChange(next: Locale) {
    if (next === locale) return;
    setLocale(next);
    startTransition(() => router.refresh());
  }

  return (
    <SegmentedControl<Locale>
      label={t.label}
      size="sm"
      className={className}
      value={locale}
      onChange={handleChange}
      options={[
        { value: "th", label: t.thai, ariaLabel: t.thaiName },
        { value: "en", label: t.english, ariaLabel: t.englishName },
      ]}
    />
  );
}
