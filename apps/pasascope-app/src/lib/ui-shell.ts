"use client";

import { useAppMode } from "@/lib/app-mode";

/** Build-time switch for the chat-first shell; off unless explicitly enabled. */
export function isChatShellFlagOn(): boolean {
  return process.env.NEXT_PUBLIC_CHAT_SHELL === "true";
}

/**
 * The chat shell follows the public workflow (sign up, no review gates), so it
 * is used only when the flag is on and the running API is in that mode. Every
 * other configuration keeps the workbench shell.
 */
export function useChatShellEnabled(): boolean {
  const mode = useAppMode();
  return isChatShellFlagOn() && mode.publicSignup && mode.openGates;
}
