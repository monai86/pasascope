import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { routerReplace } from "@/__tests__/setup";
import { SupabaseWorkspaceAccessGate } from "@/components/supabase-workspace-access-gate";

vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => null,
}));

describe("SupabaseWorkspaceAccessGate", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    routerReplace.mockClear();
  });

  it("opens the workspace for a signed-in account", () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_001",
      email: "clinician@example.test",
      role: "therapist",
      aal: "aal1",
    }));

    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    expect(screen.getByText("Unlocked workspace")).toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
  });

  it("restores workspace access from Supabase localStorage when the access-session cache is stale signed_out", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "signed_out",
    }));
    window.localStorage.setItem("sb-cbhwxklvcpgizeqriqxi-auth-token", JSON.stringify({
      access_token: createUnsignedJwt({ aal: "aal1" }),
      aal: "aal1",
      user: {
        id: "user_001",
        email: "clinician@example.test",
      },
    }));

    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    expect(await screen.findByText("Unlocked workspace")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("pasascope.supabase-access-session.v1")).toContain("\"stage\":\"authenticated\"");
    expect(window.sessionStorage.getItem("pasascope.supabase-session-token.v1")).toBeTruthy();
  });

  it("asks for the authenticator code before opening the workspace of an account with two-step verification", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "mfa_required",
      userId: "user_001",
      email: "clinician@example.test",
      role: "therapist",
      aal: "aal1",
    }));

    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    expect(await screen.findByRole("heading", { name: "Enter your verification code" })).toBeInTheDocument();
    expect(screen.queryByText("Unlocked workspace")).not.toBeInTheDocument();
    expect(routerReplace).not.toHaveBeenCalled();
  });

  it("sends a session left by the organization-based app to sign in", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "org_selection_required",
      email: "clinician@example.test",
    }));

    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    await waitFor(() => expect(routerReplace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("Unlocked workspace")).not.toBeInTheDocument();
  });

  it("automatically redirects unauthenticated visitors to /login", async () => {
    render(
      <SupabaseWorkspaceAccessGate>
        <div>Unlocked workspace</div>
      </SupabaseWorkspaceAccessGate>,
    );

    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith("/login");
    });
    expect(screen.getByRole("status")).toHaveTextContent("Taking you to sign in…");
    expect(screen.queryByText("Unlocked workspace")).not.toBeInTheDocument();
  });
});

function createUnsignedJwt(payload: Record<string, unknown>): string {
  return [
    btoa(JSON.stringify({ alg: "none", typ: "JWT" })),
    btoa(JSON.stringify(payload)),
    "",
  ].join(".");
}
