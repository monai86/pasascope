import type { LucideIcon } from "lucide-react";
import { FileText, FolderOpen, Home, Settings2 } from "lucide-react";

import type { ShellActive } from "@/services/navigation/workbench-navigation";

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

/** Which chat destination is current for a page that declares a workbench one. */
export function chatNavigationKeyFor(active: ShellActive): ChatNavigationKey {
  if (active === "Cases" || active === "Session") return "cases";
  if (active === "Reports") return "reports";
  if (active === "Settings") return "settings";
  return "home";
}
