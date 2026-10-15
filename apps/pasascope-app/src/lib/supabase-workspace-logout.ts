"use client";

import { saveSupabaseAccessSession } from "@/lib/supabase-access-session";
import { saveSupabaseBrowserAuthSnapshot } from "@/lib/supabase-browser-auth";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { saveSupabaseSessionToken } from "@/lib/supabase-session-token";

/** Written by the organization-based app; it held the account's email, so sign-out still clears it. */
const LEGACY_ORGANIZATION_HINT_KEY = "pasascope.supabase-organization-hint.v1";

export async function signOutSupabaseWorkspace(): Promise<void> {
  saveSupabaseSessionToken(null);
  saveSupabaseBrowserAuthSnapshot(null);
  saveSupabaseAccessSession({ stage: "signed_out" });
  try {
    window.localStorage.removeItem(LEGACY_ORGANIZATION_HINT_KEY);
  } catch {
    // Blocked storage must not stop sign-out.
  }
  await getSupabaseBrowserClient()?.auth.signOut?.().catch(() => undefined);
}
