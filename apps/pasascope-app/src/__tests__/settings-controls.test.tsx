import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TherapistSettings } from "@/features/settings/components/therapist-settings";
import { DEFAULT_PREFERENCES, loadPreferences } from "@/lib/preferences";

const runtime = vi.hoisted(() => ({ authMode: "supabase" as "supabase" | "mock" }));
const auth = vi.hoisted(() => ({
  updateUser: vi.fn(),
  signOut: vi.fn(),
}));
const router = vi.hoisted(() => ({ replace: vi.fn(), refresh: vi.fn() }));
const signOutWorkspace = vi.hoisted(() => vi.fn(async () => undefined));

vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/confirmed-runtime-settings", () => ({
  useConfirmedRuntimeSettings: () => ({ auth_mode: runtime.authMode }),
}));
vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({ status: "success", mode: "backend", data: { pipeline_settings: { transcription_external: true } } }),
}));
vi.mock("@/lib/use-supabase-access-session", () => ({
  useSupabaseAccessSession: () => ({ stage: "authenticated", displayName: "Khun Aom", email: "aom@example.test" }),
}));
vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({ auth }),
}));
vi.mock("@/lib/supabase-workspace-logout", () => ({ signOutSupabaseWorkspace: signOutWorkspace }));

beforeEach(() => {
  runtime.authMode = "supabase";
  window.localStorage.clear();
  delete document.documentElement.dataset.textSize;
  delete document.documentElement.dataset.motion;
  auth.updateUser.mockReset().mockResolvedValue({ data: {}, error: null });
  auth.signOut.mockReset().mockResolvedValue({ error: null });
  router.replace.mockReset();
  signOutWorkspace.mockClear();
});

afterEach(cleanup);

describe("Settings: Account", () => {
  it("shows the signed-in email and saves a new display name to the account", async () => {
    render(<TherapistSettings section="account" />);

    expect(screen.getByText("aom@example.test")).toBeInTheDocument();
    const name = screen.getByLabelText("Display name");
    expect(name).toHaveValue("Khun Aom");
    // Saving the name it already has sends nothing.
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    expect(auth.updateUser).not.toHaveBeenCalled();

    fireEvent.change(name, { target: { value: "  Khun Aom S.  " } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));

    await screen.findByText("Name saved.");
    expect(auth.updateUser).toHaveBeenCalledWith({ data: { display_name: "Khun Aom S." } });
  });

  it("refuses an empty name and reports a failed save", async () => {
    render(<TherapistSettings section="account" />);
    const name = screen.getByLabelText("Display name");

    fireEvent.change(name, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    expect(await screen.findByText("Enter a name.")).toBeInTheDocument();
    expect(auth.updateUser).not.toHaveBeenCalled();

    auth.updateUser.mockResolvedValue({ data: {}, error: { message: "boom" } });
    fireEvent.change(name, { target: { value: "Aom" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    expect(await screen.findByText("The name could not be saved. Try again.")).toBeInTheDocument();
  });

  it("offers nothing to change without real sign-in", () => {
    runtime.authMode = "mock";
    render(<TherapistSettings section="account" />);

    expect(screen.queryByLabelText("Display name")).not.toBeInTheDocument();
    expect(screen.getByText(/no account to change/)).toBeInTheDocument();
  });
});

describe("Settings: Display and Workflow", () => {
  it("keeps text size and motion in this browser and puts them on the page", () => {
    render(<TherapistSettings section="display" />);

    fireEvent.click(screen.getByRole("button", { name: "Large" }));
    fireEvent.click(screen.getByRole("button", { name: "Reduce" }));

    expect(document.documentElement.dataset.textSize).toBe("large");
    expect(document.documentElement.dataset.motion).toBe("reduce");
    expect(loadPreferences()).toEqual({ ...DEFAULT_PREFERENCES, textSize: "large", motion: "reduce" });
    expect(screen.getByRole("button", { name: "Large" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: "Standard" }));
    expect(document.documentElement.dataset.textSize).toBeUndefined();
  });

  it("keeps the language of a new case and states how work is processed", () => {
    render(<TherapistSettings section="workflow" />);

    fireEvent.click(screen.getByRole("button", { name: "English" }));

    expect(loadPreferences().caseLanguage).toBe("English");
    expect(screen.getByText("Recordings are sent to an external service to be transcribed")).toBeInTheDocument();
  });

  it("falls back to the defaults when stored preferences are unreadable", () => {
    window.localStorage.setItem("pasascope.preferences.v1", "{not json");
    expect(loadPreferences()).toEqual(DEFAULT_PREFERENCES);
    window.localStorage.setItem("pasascope.preferences.v1", JSON.stringify({ textSize: "huge", caseLanguage: "English" }));
    expect(loadPreferences()).toEqual({ ...DEFAULT_PREFERENCES, caseLanguage: "English" });
  });
});

describe("Settings: Privacy & Security", () => {
  function fillPasswords(first: string, second: string) {
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: first } });
    fireEvent.change(screen.getByLabelText("Repeat the new password"), { target: { value: second } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));
  }

  it("checks the new password before sending it, then changes it", async () => {
    render(<TherapistSettings section="privacy" />);

    fillPasswords("short", "short");
    expect(await screen.findByText("Use at least 8 characters.")).toBeInTheDocument();
    fillPasswords("long enough", "long enougj");
    expect(await screen.findByText("The two passwords are not the same.")).toBeInTheDocument();
    expect(auth.updateUser).not.toHaveBeenCalled();

    fillPasswords("long enough", "long enough");
    expect(await screen.findByText("Password changed.")).toBeInTheDocument();
    expect(auth.updateUser).toHaveBeenCalledWith({ password: "long enough" });
    expect(screen.getByLabelText("New password")).toHaveValue("");
  });

  it("explains a refused password change", async () => {
    auth.updateUser.mockResolvedValue({ data: {}, error: { code: "same_password", message: "same" } });
    render(<TherapistSettings section="privacy" />);

    fillPasswords("long enough", "long enough");

    expect(await screen.findByText("Choose a password you have not used for this account.")).toBeInTheDocument();
  });

  it("signs out of every session and returns to sign-in", async () => {
    render(<TherapistSettings section="privacy" />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Sign out everywhere" }));
    });

    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
    expect(auth.signOut).toHaveBeenCalledWith({ scope: "global" });
    expect(signOutWorkspace).toHaveBeenCalled();
  });

  it("stays signed in and says so when signing out everywhere fails", async () => {
    auth.signOut.mockResolvedValue({ error: { message: "offline" } });
    render(<TherapistSettings section="privacy" />);

    fireEvent.click(screen.getByRole("button", { name: "Sign out everywhere" }));

    expect(await screen.findByText(/Could not sign out everywhere/)).toBeInTheDocument();
    expect(router.replace).not.toHaveBeenCalled();
    expect(signOutWorkspace).not.toHaveBeenCalled();
  });
});
