import type { LucideIcon } from "lucide-react";
import { FileText, FolderOpen, Home, Settings2 } from "lucide-react";

/** What a page tells the shell it is. */
export type ShellActive = "Home" | "Cases" | "Session" | "Reports" | "Settings";

export type ChatNavigationKey = "home" | "cases" | "reports" | "settings";

export type ChatNavigationItem = {
  href: string;
  key: ChatNavigationKey;
  icon: LucideIcon;
};

/** The chat shell's destinations. A session belongs to its case, so there is no Session entry. */
export const CHAT_NAVIGATION: readonly ChatNavigationItem[] = [
  { href: "/", key: "home", icon: Home },
  { href: "/cases", key: "cases", icon: FolderOpen },
  { href: "/reports", key: "reports", icon: FileText },
  { href: "/settings", key: "settings", icon: Settings2 },
];

/** Which destination is current for a page. A session is shown under Cases. */
export function chatNavigationKeyFor(active: ShellActive): ChatNavigationKey {
  if (active === "Cases" || active === "Session") return "cases";
  if (active === "Reports") return "reports";
  if (active === "Settings") return "settings";
  return "home";
}
