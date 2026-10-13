"use client";

import Link from "next/link";
import { useCallback, useMemo, useState, type ReactNode } from "react";
import { ArrowLeft, Menu, X } from "lucide-react";

import { ChatNav } from "@/components/chat-shell/chat-nav";
import { chatShellMessages } from "@/components/chat-shell/chat-shell.messages";
import {
  ChatShellContext,
  type ChatShellHeaderState,
  type ChatShellPanelTrigger,
} from "@/components/chat-shell/chat-shell-context";
import { LanguageToggle } from "@/components/language-toggle";
import { shellMessages } from "@/components/shell.messages";
import { useFocusTrap } from "@/components/ui/use-focus-trap";
import { useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";
import { chatNavigationKeyFor, type ShellActive } from "@/services/navigation/chat-navigation";

const NAV_ID = "chat-navigation";
const PANEL_ID = "chat-side-panel";
const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";
const ROUND_CONTROL = cn(
  "grid h-11 w-11 shrink-0 place-items-center rounded-full text-ink transition hover:bg-surface motion-reduce:transition-none",
  FOCUS_RING,
);

/**
 * The chat shell's frame: navigation, the page, and an optional side panel,
 * inside one rounded frame on the canvas. Navigation is a drawer below `lg`;
 * the side panel is a sheet below `xl`, opened from the header.
 */
export function ChatShellFrame({ children, active }: { children: ReactNode; active: ShellActive }) {
  const t = useMessages(shellMessages);
  const chat = useMessages(chatShellMessages);
  const [navOpen, setNavOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [panelHost, setPanelHost] = useState<HTMLElement | null>(null);
  const [panelTrigger, setPanelTriggerState] = useState<ChatShellPanelTrigger | null>(null);
  const [header, setHeader] = useState<ChatShellHeaderState | null>(null);
  // Focus stays inside an open drawer or sheet and returns to its button on
  // close; Escape closes it.
  const navRef = useFocusTrap<HTMLElement>(navOpen, () => setNavOpen(false));
  const panelRef = useFocusTrap<HTMLElement>(panelOpen, () => setPanelOpen(false));

  const setPanelTrigger = useCallback((trigger: ChatShellPanelTrigger | null) => {
    setPanelTriggerState(trigger);
    if (trigger === null) setPanelOpen(false);
  }, []);
  const shell = useMemo(
    () => ({ panelHost, setPanelTrigger, setHeader }),
    [panelHost, setPanelTrigger],
  );
  const hasPanel = panelTrigger !== null;
  const PanelIcon = panelTrigger?.icon;

  return (
    <ChatShellContext.Provider value={shell}>
      <div data-shell="chat" className="chat-canvas flex h-dvh w-full overflow-hidden text-ink md:p-4 xl:p-5">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[80] focus:rounded-full focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-ink focus:shadow-lift"
        >
          {t.skipToContent}
        </a>

        {navOpen || panelOpen ? (
          <div
            className={cn("fixed inset-0 z-50 shell-scrim", navOpen ? "lg:hidden" : "xl:hidden")}
            aria-hidden="true"
            onClick={() => {
              setNavOpen(false);
              setPanelOpen(false);
            }}
          />
        ) : null}

        <div className="chat-frame flex min-w-0 flex-1 overflow-hidden md:rounded-shell xl:rounded-chat-frame">
          <ChatNav
            id={NAV_ID}
            active={chatNavigationKeyFor(active)}
            isOpen={navOpen}
            onClose={() => setNavOpen(false)}
            drawerRef={navRef}
          />

          <div className="flex min-w-0 flex-1 flex-col">
            {/* Phone and tablet header. Between `lg` and `xl` only the panel
                button remains, since the navigation column is on screen. */}
            <header
              className={cn(
                "flex shrink-0 items-center gap-1 px-2 py-2 md:px-4 md:pt-4",
                hasPanel ? "xl:hidden" : "lg:hidden",
              )}
            >
              {header ? (
                <>
                  <Link href={header.backHref} aria-label={chat.backHome} className={cn(ROUND_CONTROL, "lg:hidden")}>
                    <ArrowLeft size={20} aria-hidden="true" />
                  </Link>
                  <div className="min-w-0 flex-1 leading-snug">
                    <p className="truncate font-display text-lg font-semibold text-ink md:text-xl">{header.title}</p>
                    {header.subtitle ? <p className="truncate text-[13px] text-ink-subtle">{header.subtitle}</p> : null}
                  </div>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    aria-label={navOpen ? t.closeMenu : t.openMenu}
                    aria-expanded={navOpen}
                    aria-controls={NAV_ID}
                    onClick={() => setNavOpen(!navOpen)}
                    className={cn(ROUND_CONTROL, "lg:hidden")}
                  >
                    {navOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
                  </button>
                  <span className="font-display text-lg font-semibold text-ink lg:hidden">PasaScope</span>
                  <span className="flex-1" />
                </>
              )}

              {panelTrigger && PanelIcon ? (
                // An icon alone on a phone, where the header has no room for
                // the words; the label stays its accessible name throughout.
                <button
                  type="button"
                  aria-label={panelTrigger.label}
                  aria-expanded={panelOpen}
                  aria-controls={PANEL_ID}
                  onClick={() => setPanelOpen(true)}
                  className={cn(
                    "inline-flex h-11 min-w-11 shrink-0 items-center justify-center gap-2 rounded-full bg-surface text-sm font-medium text-ink shadow-chat-card transition hover:shadow-soft motion-reduce:transition-none sm:px-4",
                    FOCUS_RING,
                  )}
                >
                  <PanelIcon size={18} aria-hidden="true" className="sm:hidden" />
                  <span aria-hidden="true" className="hidden sm:inline">{panelTrigger.label}</span>
                </button>
              ) : null}
              {header ? null : <LanguageToggle className="ml-1 lg:hidden" />}
            </header>

            <main id="main-content" className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto">
              <div className="chat-page-in flex w-full flex-1 flex-col px-4 pb-4 pt-2 md:px-6 md:pb-6 lg:px-10 lg:pt-7">
                {children}
              </div>
            </main>
          </div>

          <aside
            id={PANEL_ID}
            ref={panelRef}
            // A sheet below `xl`, hidden from the tab order while closed; a
            // column of the frame from `xl`. Absent when no page fills it.
            className={cn(
              "fixed inset-y-0 right-0 z-[60] w-[min(22rem,100vw)] flex-col overflow-y-auto bg-surface p-5 transition-[transform,visibility] duration-200 motion-reduce:transition-none xl:visible xl:static xl:z-auto xl:my-5 xl:mr-5 xl:w-[300px] xl:shrink-0 xl:translate-x-0 xl:rounded-panel",
              hasPanel ? "flex" : "hidden",
              panelOpen ? "visible translate-x-0 shadow-floating xl:shadow-none" : "invisible translate-x-full",
            )}
          >
            <button
              type="button"
              aria-label={chat.closePanel}
              onClick={() => setPanelOpen(false)}
              className={cn(ROUND_CONTROL, "-mr-2 -mt-2 self-end xl:hidden")}
            >
              <X size={20} aria-hidden="true" />
            </button>
            <div ref={setPanelHost} className="flex min-h-0 flex-1 flex-col" />
          </aside>
        </div>
      </div>
    </ChatShellContext.Provider>
  );
}
