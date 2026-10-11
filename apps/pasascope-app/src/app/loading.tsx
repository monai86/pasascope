"use client";

import { routeStateMessages } from "@/app/route-states.messages";
import { useMessages } from "@/i18n/locale-provider";

// A loading file is a Suspense fallback, so it renders synchronously and takes
// the language from the provider instead of awaiting the request cookie.
export default function RouteLoading() {
  const t = useMessages(routeStateMessages);

  return (
    <main className="app-canvas flex min-h-dvh items-center justify-center p-4" role="status" aria-live="polite">
      <div className="flex items-center gap-3 rounded-full border border-line bg-surface px-5 py-3 text-sm font-medium text-ink-muted shadow-soft">
        <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-brand-border border-t-brand motion-reduce:animate-none" />
        {t.loading}
      </div>
    </main>
  );
}
