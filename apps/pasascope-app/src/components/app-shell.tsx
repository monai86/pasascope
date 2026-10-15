"use client";

import { useState, useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";

import { ChatShellFrame } from "@/components/chat-shell/chat-shell-frame";
import { shellMessages } from "@/components/shell.messages";
import { Button } from "@/components/ui/button";
import { useMessages } from "@/i18n/locale-provider";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseWorkspaceAccessGate } from "@/components/supabase-workspace-access-gate";
import { ConfirmedRuntimeSettingsProvider } from "@/lib/confirmed-runtime-settings";
import { loadMockAccessSession } from "@/lib/mock-access-session";
import { loadOrRestoreSupabaseAccessSession, useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import type { ShellActive } from "@/services/navigation/chat-navigation";

export type { ShellActive };

const SLOW_START_HINT_MS = 4000;

export function AppShell({
  children,
  active = "Home",
}: {
  children: ReactNode;
  active?: ShellActive;
}) {
  const router = useRouter();
  const t = useMessages(shellMessages);
  const runtimeSettings = useRuntimeSettings();
  const confirmedRuntimeSettings = runtimeSettings.status === "success" ? runtimeSettings.data : null;
  const supabaseSession = useSupabaseAccessSession();
  // A host that sleeps when idle takes a while to answer its first request.
  const [slowStart, setSlowStart] = useState(false);
  const settingsLoading = runtimeSettings.status === "loading";
  useEffect(() => {
    if (!settingsLoading) return;
    const timer = window.setTimeout(() => setSlowStart(true), SLOW_START_HINT_MS);
    return () => window.clearTimeout(timer);
  }, [settingsLoading]);

  useEffect(() => {
    // If returning from an OAuth callback (?code=... or #access_token=...), wait for Supabase to exchange token
    if (typeof window !== "undefined") {
      const search = window.location.search;
      const hash = window.location.hash;
      if (search.includes("code=") || hash.includes("access_token=")) {
        return;
      }
    }

    // If user is completely unauthenticated on the client, redirect directly to /login
    const restored = loadOrRestoreSupabaseAccessSession();
    const mock = loadMockAccessSession();
    if (!mock && (!restored || restored.stage === "signed_out")) {
      router.replace("/login");
    }
  }, [router, supabaseSession]);

  const supabaseGateRequired =
    confirmedRuntimeSettings?.auth_mode === "supabase" &&
    supabaseSession?.stage !== "authenticated";

  // Workspace content stays hidden until the API has said how access works.
  // Waiting for that answer is not a refusal, so it is shown as loading.
  if (runtimeSettings.status === "loading") {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-4 text-center" role="status">
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-action" aria-hidden="true" />
        <p className="text-base font-semibold text-ink">{t.opening.title}</p>
        <p className={`text-sm text-ink-muted ${slowStart ? "" : "invisible"}`}>{t.opening.waking}</p>
      </main>
    );
  }

  if (runtimeSettings.status !== "success") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-panel border border-line bg-surface p-6 text-ink shadow-lift" role="alert">
          <h1 className="text-2xl font-semibold text-ink">{t.unreachable.title}</h1>
          <p className="mt-3 text-sm leading-6 text-ink-muted">{t.unreachable.description}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button onClick={() => window.location.reload()}>{t.unreachable.retry}</Button>
            <Button href="/login" variant="secondary">{t.unreachable.goToLogin}</Button>
          </div>
        </section>
      </main>
    );
  }

  if (supabaseGateRequired) {
    return (
      <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
        <SupabaseAuthRuntimeBridge />
        <SupabaseWorkspaceAccessGate>{children}</SupabaseWorkspaceAccessGate>
      </ConfirmedRuntimeSettingsProvider>
    );
  }

  return (
    <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
      <SupabaseAuthRuntimeBridge />
      <ChatShellFrame active={active}>{children}</ChatShellFrame>
    </ConfirmedRuntimeSettingsProvider>
  );
}
