"use client";

import "@/lib/storage-key-migration";

export const SUPABASE_ACCESS_SESSION_KEY = "pasascope.supabase-access-session.v1";
export const SUPABASE_ACCESS_SESSION_EVENT = "pasascope:supabase-access-session-changed";

/** Every signed-in account is a therapist in a workspace of its own. */
export type SupabaseSessionRole = "therapist";

export type SupabaseAccessStage = "signed_out" | "authenticated";

export type SupabaseAccessSession = {
  stage: SupabaseAccessStage;
  userId?: string;
  email?: string;
  displayName?: string;
  role?: SupabaseSessionRole;
  aal?: "aal1" | "aal2";
};

export function loadSupabaseAccessSession(): SupabaseAccessSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SUPABASE_ACCESS_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SupabaseAccessSession>;
    if (!isValidStage(parsed.stage)) return null;
    return {
      stage: parsed.stage,
      userId: typeof parsed.userId === "string" ? parsed.userId : undefined,
      email: typeof parsed.email === "string" ? parsed.email : undefined,
      displayName: typeof parsed.displayName === "string" ? parsed.displayName : undefined,
      role: parsed.role === "therapist" ? parsed.role : undefined,
      aal: parsed.aal === "aal1" || parsed.aal === "aal2" ? parsed.aal : undefined,
    };
  } catch {
    return null;
  }
}

export function saveSupabaseAccessSession(session: SupabaseAccessSession): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(SUPABASE_ACCESS_SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new CustomEvent(SUPABASE_ACCESS_SESSION_EVENT, { detail: session }));
}

function isValidStage(value: unknown): value is SupabaseAccessStage {
  return value === "signed_out" || value === "authenticated";
}
