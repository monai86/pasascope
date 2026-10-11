import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";

import type { Locale } from "@/i18n/config";
import { LocaleProvider } from "@/i18n/locale-provider";

/** Renders under an explicit interface language instead of the pinned English. */
export function renderWithLocale(ui: ReactElement, locale: Locale, options?: RenderOptions): RenderResult {
  return render(<LocaleProvider initialLocale={locale}>{ui}</LocaleProvider>, options);
}
