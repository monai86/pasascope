"use client";

import type { Locale } from "@/i18n/config";
import { LocaleProvider } from "@/i18n/locale-provider";

export function Providers({ children, initialLocale }: { children: React.ReactNode; initialLocale: Locale }) {
  return <LocaleProvider initialLocale={initialLocale}>{children}</LocaleProvider>;
}
