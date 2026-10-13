"use client";

import { createContext, useContext, useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { LucideIcon } from "lucide-react";

export type ChatShellHeaderState = {
  /** Where the back arrow goes on phone and tablet. */
  backHref: string;
  title: string;
  subtitle?: string;
};

/** The header button that opens the side panel as a sheet: its name, and its icon on a phone. */
export type ChatShellPanelTrigger = { label: string; icon: LucideIcon };

export type ChatShellContextValue = {
  /** The element the side panel's content is rendered into. */
  panelHost: HTMLElement | null;
  setPanelTrigger: (trigger: ChatShellPanelTrigger | null) => void;
  setHeader: (header: ChatShellHeaderState | null) => void;
};

export const ChatShellContext = createContext<ChatShellContextValue | null>(null);

/**
 * Content for the shell's side panel: a column on a wide screen, a sheet
 * opened from the header elsewhere. `triggerLabel` names the button that
 * opens the sheet; on a phone the button shows `triggerIcon` alone. Renders
 * nothing outside the chat shell.
 */
export function ChatShellPanel({
  triggerLabel,
  triggerIcon,
  children,
}: {
  triggerLabel: string;
  triggerIcon: LucideIcon;
  children: ReactNode;
}) {
  const shell = useContext(ChatShellContext);
  const setPanelTrigger = shell?.setPanelTrigger;

  useEffect(() => {
    if (!setPanelTrigger) return;
    setPanelTrigger({ label: triggerLabel, icon: triggerIcon });
    return () => setPanelTrigger(null);
  }, [setPanelTrigger, triggerLabel, triggerIcon]);

  if (!shell?.panelHost) return null;
  return createPortal(children, shell.panelHost);
}

/**
 * Replaces the brand in the phone and tablet header with a back arrow and the
 * page's own title, as a conversation does. Renders nothing itself.
 */
export function ChatShellHeader({ backHref, title, subtitle }: ChatShellHeaderState) {
  const setHeader = useContext(ChatShellContext)?.setHeader;

  useEffect(() => {
    if (!setHeader) return;
    setHeader({ backHref, title, subtitle });
    return () => setHeader(null);
  }, [setHeader, backHref, title, subtitle]);

  return null;
}
