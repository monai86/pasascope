import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildSupabaseBrowserAuthSnapshotFromSession,
  deriveSupabaseAccessSession,
  resolveAalFromSession,
  syncSupabaseAccessSessionFromBrowserAuth,
  syncSupabaseAccessSessionFromSession,
} from "@/lib/supabase-browser-auth";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";

function jwtWithPayload(payload: Record<string, unknown>): string {
  const encode = (value: unknown) => btoa(JSON.stringify(value)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${encode({ alg: "none" })}.${encode(payload)}.signature`;
}

beforeEach(() => {
  window.sessionStorage.clear();
});

describe("supabase browser auth bridge", () => {
  it("derives a signed-out access state when no browser auth snapshot exists", () => {
    expect(deriveSupabaseAccessSession(null)).toEqual({ stage: "signed_out" });
  });

  it("derives an authenticated therapist for any signed-in account", () => {
    expect(deriveSupabaseAccessSession({
      userId: "user_001",
      email: "clinician@example.test",
      displayName: "Clinician",
      aal: "aal1",
    })).toEqual({
      stage: "authenticated",
      userId: "user_001",
      email: "clinician@example.test",
      displayName: "Clinician",
      role: "therapist",
      aal: "aal1",
    });
  });

  it("builds a browser-auth snapshot from a Supabase-like session payload", () => {
    expect(buildSupabaseBrowserAuthSnapshotFromSession({
      aal: "aal2",
      user: {
        id: "user_001",
        email: "clinician@example.test",
        user_metadata: { full_name: "Clinician" },
      },
    })).toEqual({
      userId: "user_001",
      email: "clinician@example.test",
      displayName: "Clinician",
      aal: "aal2",
    });
  });

  it("reads the assurance level from the access token when the session does not say", () => {
    const session = { access_token: jwtWithPayload({ aal: "aal2" }), user: { id: "u", email: "u@example.test" } };

    expect(resolveAalFromSession(session)).toBe("aal2");
    expect(buildSupabaseBrowserAuthSnapshotFromSession(session)?.aal).toBe("aal2");
  });

  it("treats a session with no assurance level as aal1", () => {
    expect(buildSupabaseBrowserAuthSnapshotFromSession({
      access_token: "not-a-jwt",
      user: { id: "user_001", email: "clinician@example.test" },
    })?.aal).toBe("aal1");
  });

  it("syncs access state and the token from a Supabase-like session payload", () => {
    const accessSession = syncSupabaseAccessSessionFromSession({
      aal: "aal1",
      access_token: "supabase-access-token",
      user: {
        id: "user_001",
        email: "clinician@example.test",
        user_metadata: { display_name: "Clinician" },
      },
    });

    expect(accessSession).toMatchObject({ stage: "authenticated", email: "clinician@example.test" });
    expect(window.sessionStorage.getItem("pasascope.supabase-browser-auth.v1")).toContain("\"Clinician\"");
    expect(window.sessionStorage.getItem("pasascope.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    expect(window.sessionStorage.getItem("pasascope.supabase-session-token.v1")).toBe("supabase-access-token");
  });

  it("signs out and clears the cached token when the session has no user", () => {
    syncSupabaseAccessSessionFromSession({
      aal: "aal1",
      access_token: "valid-access-token",
      user: { id: "user_001", email: "clinician@example.test" },
    });

    const signedOut = syncSupabaseAccessSessionFromSession({ access_token: "stale-access-token", user: null });

    expect(signedOut).toEqual({ stage: "signed_out" });
    expect(window.sessionStorage.getItem("pasascope.supabase-browser-auth.v1")).toBeNull();
    expect(window.sessionStorage.getItem("pasascope.supabase-access-session.v1")).toContain("\"stage\":\"signed_out\"");
    expect(window.sessionStorage.getItem("pasascope.supabase-session-token.v1")).toBeNull();
  });

  it("ignores a snapshot stored by the earlier organization-based app", () => {
    window.sessionStorage.setItem("pasascope.supabase-browser-auth.v1", JSON.stringify({
      userId: "user_001",
      email: "clinician@example.test",
      aal: "aal7",
      appMetadata: { role: "org_admin", organization_id: "clinic_001" },
    }));

    expect(syncSupabaseAccessSessionFromBrowserAuth()).toEqual({ stage: "signed_out" });
  });

  it("publishes a Supabase session payload event for the runtime bridge to consume", () => {
    const listener = vi.fn();
    window.addEventListener("pasascope:supabase-session-source", listener as EventListener);

    publishSupabaseSessionPayload({
      user: { id: "user_001", email: "clinician@example.test" },
      aal: "aal2",
    });

    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener("pasascope:supabase-session-source", listener as EventListener);
  });
});
