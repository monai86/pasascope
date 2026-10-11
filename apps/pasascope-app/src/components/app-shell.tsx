"use client";

import { useState, useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Menu, X } from "lucide-react";

import { Sidebar, type ShellActive } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { BottomNav } from "@/components/bottom-nav";
import { LanguageToggle } from "@/components/language-toggle";
import { RightRail } from "@/components/right-rail";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { shellMessages } from "@/components/shell.messages";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { useFocusTrap } from "@/components/ui/use-focus-trap";
import { useMessages } from "@/i18n/locale-provider";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseWorkspaceAccessGate } from "@/components/supabase-workspace-access-gate";
import { WorkspaceAccessGate } from "@/components/workspace-access-gate";
import { ConfirmedRuntimeSettingsProvider } from "@/lib/confirmed-runtime-settings";
import { loadMockAccessSession } from "@/lib/mock-access-session";
import { loadOrRestoreSupabaseAccessSession, useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export type { ShellActive };

const SIDEBAR_ID = "primary-sidebar";

export function AppShell({
  children,
  active = "Today",
  activeSessionId,
  activeCaseId,
  rightRail,
}: {
  children: ReactNode;
  active?: ShellActive;
  activeSessionId?: string;
  activeCaseId?: string;
  rightRail?: ReactNode;
}) {
  const router = useRouter();
  const t = useMessages(shellMessages);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Focus stays inside the mobile drawer while it is open and returns to the
  // menu button when it closes; Escape closes it.
  const drawerRef = useFocusTrap<HTMLElement>(sidebarOpen, () => setSidebarOpen(false));
  const runtimeSettings = useRuntimeSettings();
  const confirmedRuntimeSettings = runtimeSettings.status === "success" ? runtimeSettings.data : null;
  const session = typeof window !== "undefined" ? loadMockAccessSession() : null;
  const supabaseSession = useSupabaseAccessSession();

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

  const gateRequired = confirmedRuntimeSettings?.auth_mode === "mock" && session?.aal === "aal1";
  const mfaRequired = confirmedRuntimeSettings?.access_model?.required_app_aal === "aal2";
  const hasValidAal = mfaRequired
    ? supabaseSession?.aal === "aal2"
    : Boolean(supabaseSession?.aal && (supabaseSession.aal === "aal1" || supabaseSession.aal === "aal2"));
  const supabaseGateRequired =
    confirmedRuntimeSettings?.auth_mode === "supabase" &&
    !(
      supabaseSession?.stage === "authenticated" &&
      supabaseSession.organizationId &&
      hasValidAal
    );

  if (runtimeSettings.status !== "success") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-panel border border-line bg-surface p-6 text-ink shadow-lift" role="alert">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-subtle">{t.blocked.eyebrow}</p>
          <h1 className="mt-3 text-3xl font-semibold text-ink">{t.blocked.title}</h1>
          <p className="mt-3 text-sm leading-6 text-ink-muted">{t.blocked.description}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button href="/login">{t.blocked.goToLogin}</Button>
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

  if (gateRequired) {
    return (
      <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
        <SupabaseAuthRuntimeBridge />
        <WorkspaceAccessGate>{children}</WorkspaceAccessGate>
      </ConfirmedRuntimeSettingsProvider>
    );
  }

  return (
    <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
      <SupabaseAuthRuntimeBridge />
      <div className="app-canvas flex h-dvh w-full overflow-hidden text-ink">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[80] focus:rounded-full focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-ink focus:shadow-lift"
        >
          {t.skipToContent}
        </a>

        {sidebarOpen ? (
          <div
            className="fixed inset-0 z-50 bg-navy/45 lg:hidden"
            aria-hidden="true"
            onClick={() => setSidebarOpen(false)}
          />
        ) : null}

        <Sidebar
          id={SIDEBAR_ID}
          active={active}
          activeSessionId={activeSessionId}
          activeCaseId={activeCaseId}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          drawerRef={drawerRef}
        />

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Phone and tablet header; the desktop top bar takes over at lg. */}
          <header className="glass-chrome flex h-14 shrink-0 items-center justify-between gap-2 border-x-0 border-t-0 px-3 lg:hidden">
            <IconButton
              icon={sidebarOpen ? X : Menu}
              label={sidebarOpen ? t.closeMenu : t.openMenu}
              aria-expanded={sidebarOpen}
              aria-controls={SIDEBAR_ID}
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="border-transparent bg-transparent"
            />
            <PasaScopeLogo size="sm" showSubtitle={false} href="/today" />
            <LanguageToggle />
          </header>

          <Topbar showSearch={active !== "Cases"} />

          <main id="main-content" className="min-w-0 flex-1 overflow-y-auto p-4 max-md:pb-44 md:p-6">
            <div className="flex items-start gap-6">
              <div className="min-w-0 flex-1">{children}</div>
              {rightRail ? <RightRail>{rightRail}</RightRail> : null}
            </div>
          </main>

          {/* Mobile bottom navigation (hidden at md+ via .mobile-bottom-nav) */}
          <BottomNav active={active} activeSessionId={activeSessionId} activeCaseId={activeCaseId} />
        </div>
      </div>
    </ConfirmedRuntimeSettingsProvider>
  );
}
