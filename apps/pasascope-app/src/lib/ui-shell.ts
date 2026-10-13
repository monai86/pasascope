"use client";

import { useAppMode } from "@/lib/app-mode";

/**
 * Whether this build may use the chat shell. It may unless it was built with
 * NEXT_PUBLIC_CHAT_SHELL=false, which keeps the workbench shell everywhere:
 * the way back if the chat shell has to be withdrawn from a deployment.
 */
export function isChatShellAllowed(): boolean {
  return process.env.NEXT_PUBLIC_CHAT_SHELL !== "false";
}

/**
 * The chat shell is the interface of the public workflow (sign up, no review
 * gates), so it is used when the running API is in that mode. An API that
 * still enforces review gates keeps the workbench shell, whose screens carry
 * the attestation and sign-off steps the conversation does not have.
 */
export function useChatShellEnabled(): boolean {
  const mode = useAppMode();
  return isChatShellAllowed() && mode.publicSignup && mode.openGates;
}
