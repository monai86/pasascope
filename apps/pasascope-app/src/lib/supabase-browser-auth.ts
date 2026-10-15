"use client";

import {
  saveSupabaseAccessSession,
  type SupabaseAccessSession,
} from "@/lib/supabase-access-session";
import { saveSupabaseSessionToken } from "@/lib/supabase-session-token";

import "@/lib/storage-key-migration";

export const SUPABASE_BROWSER_AUTH_KEY = "pasascope.supabase-browser-auth.v1";
export const SUPABASE_BROWSER_AUTH_EVENT = "pasascope:supabase-browser-auth-changed";

/**
 * Who is signed in, as the screens need to know it. The API derives the
 * account's workspace from the token itself, so nothing here grants access.
 */
export type SupabaseBrowserAuthSnapshot = {
  userId: string;
  email: string;
  displayName?: string;
  aal: "aal1" | "aal2";
  /** The account has a verified authenticator, so the session has to reach aal2. */
  mfaEnrolled: boolean;
};

export type SupabaseSessionLike = {
  aal?: string | null;
  access_token?: string | null;
  user?: {
    id?: string | null;
    email?: string | null;
    factors?: ReadonlyArray<{ status?: unknown } | null> | null;
    user_metadata?: {
      display_name?: unknown;
      full_name?: unknown;
      name?: unknown;
    } | null;
  } | null;
} | null;

export function loadSupabaseBrowserAuthSnapshot(): SupabaseBrowserAuthSnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SUPABASE_BROWSER_AUTH_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<SupabaseBrowserAuthSnapshot>;
    if (!isValidSnapshot(parsed)) return null;
    return {
      userId: parsed.userId,
      email: parsed.email,
      displayName: typeof parsed.displayName === "string" ? parsed.displayName : undefined,
      aal: parsed.aal,
      mfaEnrolled: parsed.mfaEnrolled === true,
    };
  } catch {
    return null;
  }
}

export function saveSupabaseBrowserAuthSnapshot(snapshot: SupabaseBrowserAuthSnapshot | null): void {
  if (typeof window === "undefined") return;
  if (snapshot) {
    window.sessionStorage.setItem(SUPABASE_BROWSER_AUTH_KEY, JSON.stringify(snapshot));
  } else {
    window.sessionStorage.removeItem(SUPABASE_BROWSER_AUTH_KEY);
  }
  window.dispatchEvent(new CustomEvent(SUPABASE_BROWSER_AUTH_EVENT, { detail: snapshot }));
}

export function decodeAalFromJwt(token: string): "aal1" | "aal2" | null {
  try {
    const [, payloadSegment] = token.split(".");
    if (!payloadSegment) {
      return null;
    }
    const normalized = payloadSegment
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(payloadSegment.length / 4) * 4, "=");
    const decodedStr =
      typeof window !== "undefined" && typeof window.atob === "function"
        ? window.atob(normalized)
        : Buffer.from(normalized, "base64").toString("utf-8");
    const payload = JSON.parse(decodedStr) as { aal?: unknown };
    return payload.aal === "aal1" || payload.aal === "aal2" ? payload.aal : null;
  } catch {
    return null;
  }
}

export function resolveAalFromSession(session: SupabaseSessionLike): "aal1" | "aal2" | null {
  if (session?.aal === "aal1" || session?.aal === "aal2") {
    return session.aal;
  }
  if (session?.access_token) {
    const decoded = decodeAalFromJwt(session.access_token);
    if (decoded) return decoded;
  }
  return null;
}

export function buildSupabaseBrowserAuthSnapshotFromSession(
  session: SupabaseSessionLike,
): SupabaseBrowserAuthSnapshot | null {
  if (!session?.user?.id || !session.user.email) return null;
  return {
    userId: session.user.id,
    email: session.user.email,
    displayName: extractDisplayName(session.user.user_metadata),
    aal: resolveAalFromSession(session) ?? "aal1",
    mfaEnrolled: Array.isArray(session.user.factors)
      && session.user.factors.some((factor) => factor?.status === "verified"),
  };
}

export function saveSupabaseBrowserAuthSnapshotFromSession(session: SupabaseSessionLike): SupabaseBrowserAuthSnapshot | null {
  const snapshot = buildSupabaseBrowserAuthSnapshotFromSession(session);
  saveSupabaseSessionToken(snapshot ? (session?.access_token ?? null) : null);
  saveSupabaseBrowserAuthSnapshot(snapshot);
  return snapshot;
}

export function syncSupabaseAccessSessionFromBrowserAuth(): SupabaseAccessSession {
  const accessSession = deriveSupabaseAccessSession(loadSupabaseBrowserAuthSnapshot());
  saveSupabaseAccessSession(accessSession);
  return accessSession;
}

export function syncSupabaseAccessSessionFromSession(session: SupabaseSessionLike): SupabaseAccessSession {
  saveSupabaseBrowserAuthSnapshotFromSession(session);
  return syncSupabaseAccessSessionFromBrowserAuth();
}

export function deriveSupabaseAccessSession(snapshot: SupabaseBrowserAuthSnapshot | null): SupabaseAccessSession {
  if (!snapshot) {
    return { stage: "signed_out" };
  }
  return {
    // The API refuses an aal1 session of an account with two-step verification.
    stage: snapshot.mfaEnrolled && snapshot.aal !== "aal2" ? "mfa_required" : "authenticated",
    userId: snapshot.userId,
    email: snapshot.email,
    displayName: snapshot.displayName,
    role: "therapist",
    aal: snapshot.aal,
  };
}

function isValidSnapshot(value: Partial<SupabaseBrowserAuthSnapshot> | undefined): value is SupabaseBrowserAuthSnapshot {
  return Boolean(
    value
    && typeof value.userId === "string"
    && value.userId.trim()
    && typeof value.email === "string"
    && value.email.trim()
    && (value.aal === "aal1" || value.aal === "aal2")
  );
}

function extractDisplayName(
  metadata: {
    display_name?: unknown;
    full_name?: unknown;
    name?: unknown;
  } | null | undefined,
): string | undefined {
  if (!metadata || typeof metadata !== "object") return undefined;
  if (typeof metadata.display_name === "string" && metadata.display_name.trim()) return metadata.display_name;
  if (typeof metadata.full_name === "string" && metadata.full_name.trim()) return metadata.full_name;
  if (typeof metadata.name === "string" && metadata.name.trim()) return metadata.name;
  return undefined;
}
