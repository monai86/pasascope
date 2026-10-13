"use client";

import Link from "next/link";
import type { RefObject } from "react";
import { LogOut } from "lucide-react";

import { useLanguageSwitch } from "@/components/language-toggle";
import { chatShellMessages } from "@/components/chat-shell/chat-shell.messages";
import { PasaScopeLogoMark } from "@/components/pasascope-logo";
import { shellMessages } from "@/components/shell.messages";
import { useShellUser } from "@/components/use-shell-user";
import type { Locale } from "@/i18n/config";
import { useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";
import { CHAT_NAVIGATION, type ChatNavigationKey } from "@/services/navigation/chat-navigation";

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";

/**
 * The chat shell's navigation: brand, four destinations and the signed-in
 * user. A column on desktop, a drawer below `lg`.
 */
export function ChatNav({
  id,
  active,
  isOpen,
  onClose,
  drawerRef,
}: {
  id: string;
  active: ChatNavigationKey;
  isOpen: boolean;
  onClose: () => void;
  /** Receives the element that traps focus while the drawer is open. */
  drawerRef: RefObject<HTMLElement | null>;
}) {
  const t = useMessages(shellMessages);
  const chat = useMessages(chatShellMessages);

  return (
    <aside
      id={id}
      ref={drawerRef}
      // Below `lg` this is a drawer. While closed it is out of the tab order
      // and hidden from assistive technology, not merely moved off screen.
      className={cn(
        "fixed inset-y-0 left-0 z-[60] flex w-[264px] flex-col gap-7 overflow-y-auto bg-chat-frame px-5 pb-5 pt-7 transition-[transform,visibility] duration-200 motion-reduce:transition-none lg:visible lg:static lg:z-auto lg:w-[232px] lg:shrink-0 lg:translate-x-0 lg:border-r lg:border-chat-line lg:bg-transparent",
        isOpen ? "visible translate-x-0 shadow-floating lg:shadow-none" : "invisible -translate-x-full",
      )}
    >
      <Link
        href="/"
        onClick={onClose}
        className={cn("flex min-h-11 items-center gap-2.5 rounded-control px-3", FOCUS_RING)}
      >
        <PasaScopeLogoMark size="sm" />
        <span className="font-display text-xl font-semibold text-ink">PasaScope</span>
      </Link>

      <nav aria-label={t.primaryNavigation} className="flex flex-col gap-0.5">
        {CHAT_NAVIGATION.map((item) => {
          const Icon = item.icon;
          const isActive = item.key === active;
          return (
            <Link
              key={item.key}
              href={item.href}
              onClick={onClose}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex min-h-[46px] items-center gap-3.5 rounded-full px-4 transition motion-reduce:transition-none",
                FOCUS_RING,
                isActive
                  ? "bg-surface font-semibold text-ink shadow-chat-card"
                  : "text-ink-subtle hover:bg-surface hover:text-ink",
              )}
            >
              <Icon aria-hidden="true" className="h-[18px] w-[18px] shrink-0" />
              <span>{chat.nav[item.key]}</span>
            </Link>
          );
        })}
      </nav>

      <ChatUserCard />
    </aside>
  );
}

function ChatUserCard() {
  const t = useMessages(shellMessages);
  const user = useShellUser();
  const { locale, change } = useLanguageSwitch();
  const options: ReadonlyArray<{ value: Locale; label: string; name: string }> = [
    { value: "th", label: t.language.thai, name: t.language.thaiName },
    { value: "en", label: t.language.english, name: t.language.englishName },
  ];

  return (
    <div className="mt-auto flex flex-col gap-3 rounded-card bg-chat-user-card p-3.5">
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden="true"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-surface font-semibold text-ink"
        >
          {user.name.trim().charAt(0).toUpperCase()}
        </span>
        <span className="flex min-w-0 flex-1 flex-col leading-snug">
          <span className="truncate text-sm font-semibold text-ink">{user.name}</span>
          <span className="truncate text-xs text-chat-user-card-text">{user.workspace}</span>
        </span>
        {user.showLogout ? (
          <button
            type="button"
            aria-label={t.logOut}
            title={t.logOut}
            onClick={() => void user.logOut()}
            className={cn(
              "grid h-11 w-11 shrink-0 place-items-center rounded-full text-ink transition hover:bg-surface motion-reduce:transition-none",
              FOCUS_RING,
            )}
          >
            <LogOut size={18} aria-hidden="true" />
          </button>
        ) : null}
      </div>

      <div role="group" aria-label={t.language.label} className="grid grid-cols-2 rounded-full bg-white/45 p-0.5">
        {options.map((option) => {
          const selected = option.value === locale;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={selected}
              aria-label={option.name}
              onClick={() => change(option.value)}
              className={cn(
                "min-h-11 rounded-full text-sm transition motion-reduce:transition-none",
                FOCUS_RING,
                selected ? "bg-surface font-semibold text-ink" : "text-chat-user-card-text hover:text-ink",
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
