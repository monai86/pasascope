import { cleanup, render, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SUPABASE_SESSION_SOURCE_EVENT } from "@/lib/supabase-session-source";

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "supabase" },
  }),
}));

vi.mock("@/lib/supabase-auth-runtime", () => ({
  ensureSupabaseAuthRuntimeSync: () => {
    window.dispatchEvent(new CustomEvent(SUPABASE_SESSION_SOURCE_EVENT, {
      detail: {
        kind: "session",
        session: {
          aal: "aal2",
          access_token: "test-access-token",
          user: {
            id: "user_a",
            email: "user.a@example.test",
            user_metadata: {
              display_name: "User A",
            },
          },
        },
      },
    }));
  },
}));

describe("SupabaseAuthRuntimeBridge", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("captures an immediate session event emitted during runtime sync startup", async () => {
    render(<SupabaseAuthRuntimeBridge />);

    await waitFor(() => {
      expect(window.sessionStorage.getItem("pasascope.supabase-session-token.v1")).toBe("test-access-token");
      expect(window.sessionStorage.getItem("pasascope.supabase-browser-auth.v1")).toContain("\"displayName\":\"User A\"");
      expect(window.sessionStorage.getItem("pasascope.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    });
  });
});
