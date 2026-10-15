"use client";

import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";

/**
 * Two-step verification with an authenticator app (TOTP), through Supabase
 * Auth in the browser. It is optional: an account turns it on in Settings,
 * and from then on a session needs the app's code before the workspace opens.
 * The API enforces the same rule on every request.
 */

export const AUTHENTICATOR_NAME = "PasaScope";

export type TotpFactor = { id: string; friendlyName?: string };

export type VerifyOutcome = "verified" | "wrongCode" | "failed";

/** Digits only: an authenticator shows "123 456", and a pasted code may carry spaces. */
export function normalizeCode(value: string): string {
  return value.replace(/\D/g, "").slice(0, 6);
}

/** The account's verified authenticator, or null when it has none. Throws when Supabase cannot be asked. */
export async function loadVerifiedTotpFactor(): Promise<TotpFactor | null> {
  const auth = getSupabaseBrowserClient()?.auth;
  if (!auth) throw new Error("Supabase is not configured.");
  const { data, error } = await auth.mfa.listFactors();
  if (error) throw error;
  const factor = data?.totp?.find((item) => item.status === "verified");
  return factor ? { id: factor.id, friendlyName: factor.friendly_name } : null;
}

/** Checks a code; on success the session is raised to aal2 and handed to the app. */
export async function verifyTotpCode(factorId: string, code: string): Promise<VerifyOutcome> {
  const auth = getSupabaseBrowserClient()?.auth;
  if (!auth) return "failed";
  try {
    const { error } = await auth.mfa.challengeAndVerify({ factorId, code });
    if (error) {
      const known = (error as { code?: unknown }).code;
      return known === "mfa_verification_failed" || known === "mfa_challenge_expired" || error.status === 422
        ? "wrongCode"
        : "failed";
    }
    await publishCurrentSession();
    return "verified";
  } catch {
    return "failed";
  }
}

export type Enrollment = { factorId: string; qrCode: string; secret: string };

/** Starts adding an authenticator. A half-finished one from an earlier attempt is removed first. */
export async function startTotpEnrollment(): Promise<Enrollment> {
  const auth = getSupabaseBrowserClient()?.auth;
  if (!auth) throw new Error("Supabase is not configured.");
  const { data: listed, error: listError } = await auth.mfa.listFactors();
  if (listError) throw listError;
  for (const stale of listed?.all ?? []) {
    if (stale.factor_type === "totp" && stale.status === "unverified") {
      await auth.mfa.unenroll({ factorId: stale.id });
    }
  }
  const { data, error } = await auth.mfa.enroll({ factorType: "totp", friendlyName: AUTHENTICATOR_NAME });
  if (error) throw error;
  // supabase-js hands the QR code over as an SVG data URL.
  return { factorId: data.id, qrCode: data.totp.qr_code, secret: data.totp.secret };
}

/** Drops an enrollment that was started and not finished. */
export async function abandonTotpEnrollment(factorId: string): Promise<void> {
  await getSupabaseBrowserClient()?.auth.mfa.unenroll({ factorId }).catch(() => undefined);
}

/** Turns two-step verification off. Supabase allows it only from an aal2 session. */
export async function removeTotpFactor(factorId: string): Promise<boolean> {
  const auth = getSupabaseBrowserClient()?.auth;
  if (!auth) return false;
  const { error } = await auth.mfa.unenroll({ factorId });
  if (error) return false;
  // The session still lists the factor until it is refreshed.
  await auth.refreshSession().catch(() => undefined);
  await publishCurrentSession();
  return true;
}

/** Fetches the session again, so a factor added or removed elsewhere is seen. */
export async function refreshSessionFactors(): Promise<void> {
  const auth = getSupabaseBrowserClient()?.auth;
  if (!auth) return;
  await auth.refreshSession().catch(() => undefined);
  await publishCurrentSession();
}

async function publishCurrentSession(): Promise<void> {
  const auth = getSupabaseBrowserClient()?.auth;
  if (!auth) return;
  const { data } = await auth.getSession();
  publishSupabaseSessionPayload(data.session ?? null);
}
