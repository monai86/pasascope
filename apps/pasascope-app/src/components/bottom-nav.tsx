"use client";

import Link from "next/link";

import { shellMessages } from "@/components/shell.messages";
import { useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";
import { getWorkbenchNavigation, type ShellActive } from "@/services/navigation/workbench-navigation";

export function BottomNav({
  active,
  activeSessionId,
  activeCaseId,
}: {
  active: ShellActive;
  activeSessionId?: string;
  activeCaseId?: string;
}) {
  const t = useMessages(shellMessages);
  const items = getWorkbenchNavigation(activeSessionId, activeCaseId, { forBottomNav: true });

  return (
    <nav className="mobile-bottom-nav" aria-label={t.bottomNavigation}>
      <div className="glass-chrome grid grid-cols-5 rounded-panel p-1.5 shadow-lift">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.active === active;

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex min-h-11 flex-col items-center justify-center gap-1 rounded-card px-1 py-1 text-xs transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none",
                isActive ? "bg-brand-soft font-semibold text-brand-strong" : "font-medium text-ink-subtle hover:text-ink",
              )}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{t.nav[item.active]}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
