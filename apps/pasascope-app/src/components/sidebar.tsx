"use client";

import Link from "next/link";
import type { RefObject } from "react";
import { LogOut, Plus } from "lucide-react";

import { PasaScopeLogo } from "@/components/pasascope-logo";
import { shellMessages } from "@/components/shell.messages";
import { Button } from "@/components/ui/button";
import { useMessages } from "@/i18n/locale-provider";
import { APP_VERSION } from "@/lib/app-version";
import { cn } from "@/lib/cn";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { getWorkbenchNavigation, type ShellActive } from "@/services/navigation/workbench-navigation";

export type { ShellActive };

export function Sidebar({
  id,
  active,
  activeSessionId,
  activeCaseId,
  isOpen = false,
  onClose,
  drawerRef,
}: {
  /** Lets the menu button name the drawer it controls. */
  id?: string;
  active: ShellActive;
  activeSessionId?: string;
  activeCaseId?: string;
  isOpen?: boolean;
  onClose?: () => void;
  /** Receives the element that traps focus while the mobile drawer is open. */
  drawerRef?: RefObject<HTMLElement | null>;
}) {
  const t = useMessages(shellMessages);
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const showLogout =
    (runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase") ||
    Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out");

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  const navItems = getWorkbenchNavigation(activeSessionId, activeCaseId);

  return (
    <aside
      id={id}
      ref={drawerRef}
      // Below `lg` the sidebar is a drawer. While closed it is hidden from the
      // tab order and from assistive technology, not merely moved off screen.
      className={cn(
        "glass-chrome fixed inset-y-0 left-0 z-[60] flex w-[264px] flex-col border-y-0 border-l-0 transition-[transform,visibility] duration-200 motion-reduce:transition-none lg:visible lg:static lg:z-auto lg:translate-x-0",
        isOpen ? "visible translate-x-0 shadow-floating lg:shadow-none" : "invisible -translate-x-full",
      )}
    >
      <div className="px-5 pb-2 pt-5">
        <PasaScopeLogo size="md" href="/today" />
        <p className="mt-1.5 text-xs font-medium text-ink-subtle">{t.tagline}</p>
      </div>

      <div className="p-3">
        {/* Outlined, so the page's own primary action is the only solid azure button. */}
        <Button href="/cases?intent=start-session" onClick={onClose} icon={Plus} variant="secondary" className="w-full">
          {t.newSession}
        </Button>
      </div>

      <nav aria-label={t.primaryNavigation} className="flex-1 space-y-1 overflow-y-auto px-3 py-2 text-sm">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.active === active;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex min-h-11 items-center gap-3 rounded-full px-4 py-2.5 transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none",
                isActive
                  ? "bg-brand-soft font-semibold text-brand-strong"
                  : "font-medium text-ink-muted hover:bg-surface-soft hover:text-ink",
              )}
            >
              <Icon aria-hidden="true" className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-brand" : "text-ink-subtle")} />
              <span className="flex-1">{t.nav[item.active]}</span>
            </Link>
          );
        })}
      </nav>

      <div className="space-y-1 border-t border-line p-3">
        {showLogout ? (
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="flex min-h-11 w-full items-center gap-3 rounded-full px-4 py-2 text-sm font-medium text-ink-muted transition hover:bg-surface-soft hover:text-ink focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
          >
            <LogOut aria-hidden="true" className="h-[18px] w-[18px] text-ink-subtle" />
            <span>{t.logOut}</span>
          </button>
        ) : null}
        <p className="px-4 py-1 text-xs text-ink-subtle">PasaScope {APP_VERSION}</p>
      </div>
    </aside>
  );
}
