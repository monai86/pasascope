"use client";

import type { Locale } from "@/i18n/config";
import { LocaleProvider } from "@/i18n/locale-provider";
import { PreferencesBootstrap } from "@/lib/preferences";

export function Providers({ children, initialLocale }: { children: React.ReactNode; initialLocale: Locale }) {
  return (
    <LocaleProvider initialLocale={initialLocale}>
      <PreferencesBootstrap />
      {children}
    </LocaleProvider>
  );
}
