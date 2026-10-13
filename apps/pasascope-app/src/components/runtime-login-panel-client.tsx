"use client";

import { useEffect, useState } from "react";

import { loginMessages } from "@/components/login.messages";
import { MockLoginFormClient } from "@/components/mock-login-form-client";
import { Skeleton } from "@/components/skeleton";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseLoginFormClient } from "@/components/supabase-login-form-client";
import { Button } from "@/components/ui/button";
import { useMessages } from "@/i18n/locale-provider";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

const PANEL = "w-full rounded-panel bg-surface p-6 shadow-chat-card sm:p-8";
const SLOW_START_HINT_MS = 4000;

export function RuntimeLoginPanelClient() {
  const t = useMessages(loginMessages).panel;
  const runtimeSettings = useRuntimeSettings();
  // A host that sleeps when idle takes about a minute to answer its first request.
  const [slowStart, setSlowStart] = useState(false);
  const loading = runtimeSettings.status === "loading";

  useEffect(() => {
    if (!loading) return;
    const timer = window.setTimeout(() => setSlowStart(true), SLOW_START_HINT_MS);
    return () => window.clearTimeout(timer);
  }, [loading]);

  if (loading) {
    // The form's own outline, so the panel does not change size when the form arrives.
    return (
      <div className={PANEL} role="status">
        <p className="font-display text-2xl font-semibold leading-snug text-ink sm:text-[1.7rem]">{t.loading}</p>
        <p className={`mt-2 leading-relaxed text-ink-muted ${slowStart ? "" : "invisible"}`}>{t.waking}</p>
        <div className="mt-6 space-y-4" aria-hidden="true">
          <Skeleton className="h-12 w-52 rounded-full" />
          <Skeleton className="h-12 w-full rounded-control" />
          <Skeleton className="h-12 w-full rounded-control" />
          <Skeleton className="h-[52px] w-full rounded-full" />
        </div>
      </div>
    );
  }

  if (runtimeSettings.status !== "success") {
    return (
      <div className={PANEL} role="alert">
        <h2 className="font-display text-2xl font-semibold leading-snug text-ink">{t.unavailableTitle}</h2>
        <p className="mt-2 leading-relaxed text-ink-muted">{t.unavailableBody}</p>
        <Button className="mt-5" onClick={() => window.location.reload()}>{t.retry}</Button>
      </div>
    );
  }

  if (runtimeSettings.data.auth_mode === "supabase") {
    return (
      <>
        <SupabaseAuthRuntimeBridge />
        <SupabaseLoginFormClient runtimeSettings={runtimeSettings.data} />
      </>
    );
  }

  return (
    <>
      <SupabaseAuthRuntimeBridge />
      <MockLoginFormClient runtimeSettings={runtimeSettings.data} />
    </>
  );
}
