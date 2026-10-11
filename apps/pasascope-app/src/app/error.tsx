"use client";

import { routeStateMessages } from "@/app/route-states.messages";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { useMessages } from "@/i18n/locale-provider";

// The error object is deliberately not rendered or logged here: its message
// can carry request details, and clinical content must stay out of the page
// and the console. `retry` re-fetches and re-renders the failed segment.
export default function RouteError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  const t = useMessages(routeStateMessages).error;

  return (
    <main className="app-canvas flex min-h-dvh items-center justify-center p-4">
      <ErrorState
        className="w-full max-w-xl bg-surface shadow-lift"
        title={t.title}
        description={t.description}
        retryLabel={t.retry}
        onRetry={retry}
        action={<Button href="/today" variant="ghost">{t.goToToday}</Button>}
      />
    </main>
  );
}
