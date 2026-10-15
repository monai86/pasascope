import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MfaChallenge } from "@/components/mfa-challenge";
import { TherapistSettings } from "@/features/settings/components/therapist-settings";
import { normalizeCode } from "@/lib/supabase-mfa";

const access = vi.hoisted(() => ({
  model: { two_step_verification: "optional", account_deletion: "available" } as Record<string, string>,
}));
const mfa = vi.hoisted(() => ({
  listFactors: vi.fn(),
  enroll: vi.fn(),
  challengeAndVerify: vi.fn(),
  unenroll: vi.fn(),
}));
const auth = vi.hoisted(() => ({
  getSession: vi.fn(),
  refreshSession: vi.fn(),
  updateUser: vi.fn(),
  signOut: vi.fn(),
}));
const signOutWorkspace = vi.hoisted(() => vi.fn(async () => undefined));
const deleteOwnAccount = vi.hoisted(() => vi.fn());
const assign = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/confirmed-runtime-settings", () => ({
  useConfirmedRuntimeSettings: () => ({ auth_mode: "supabase", access_model: access.model }),
}));
vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({ status: "success", mode: "backend", data: { pipeline_settings: {} } }),
}));
vi.mock("@/lib/use-supabase-access-session", () => ({
  useSupabaseAccessSession: () => ({ stage: "authenticated", email: "aom@example.test" }),
}));
vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({ auth: { ...auth, mfa } }),
}));
vi.mock("@/lib/supabase-workspace-logout", () => ({ signOutSupabaseWorkspace: signOutWorkspace }));
vi.mock("@/features/settings/services/account-api", () => ({ deleteOwnAccount }));

const VERIFIED = { id: "factor-1", factor_type: "totp", status: "verified", friendly_name: "PasaScope" };

function factors(list: Array<typeof VERIFIED | { id: string; factor_type: string; status: string }>) {
  return {
    data: { all: list, totp: list.filter((item) => item.status === "verified"), phone: [], webauthn: [] },
    error: null,
  };
}

beforeEach(() => {
  access.model = { two_step_verification: "optional", account_deletion: "available" };
  for (const fn of [...Object.values(mfa), ...Object.values(auth), deleteOwnAccount, assign]) fn.mockReset();
  auth.getSession.mockResolvedValue({ data: { session: { aal: "aal2", user: { id: "u", email: "aom@example.test" } } } });
  auth.refreshSession.mockResolvedValue({ data: {}, error: null });
  mfa.unenroll.mockResolvedValue({ data: {}, error: null });
  signOutWorkspace.mockClear();
  Object.defineProperty(window, "location", { configurable: true, value: { ...window.location, assign } });
});

afterEach(cleanup);

describe("the code asked for after signing in", () => {
  it("keeps digits only", () => {
    expect(normalizeCode(" 123 456 ")).toBe("123456");
    expect(normalizeCode("12a3-4567")).toBe("123456");
  });

  it("checks the code against the account's authenticator and opens the workspace", async () => {
    const listener = vi.fn();
    window.addEventListener("pasascope:supabase-session-source", listener as EventListener);
    mfa.listFactors.mockResolvedValue(factors([VERIFIED]));
    mfa.challengeAndVerify.mockResolvedValue({ data: {}, error: null });
    render(<MfaChallenge email="aom@example.test" />);

    const field = await screen.findByLabelText("6-digit code");
    await waitFor(() => expect(field).toBeEnabled());
    fireEvent.change(field, { target: { value: "123 456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => expect(mfa.challengeAndVerify).toHaveBeenCalledWith({ factorId: "factor-1", code: "123456" }));
    await waitFor(() => expect(listener).toHaveBeenCalled());
    window.removeEventListener("pasascope:supabase-session-source", listener as EventListener);
  });

  it("asks again after a wrong code, without sending a short one", async () => {
    mfa.listFactors.mockResolvedValue(factors([VERIFIED]));
    mfa.challengeAndVerify.mockResolvedValue({ data: null, error: { code: "mfa_verification_failed", status: 422, message: "Invalid TOTP code entered" } });
    render(<MfaChallenge />);
    const field = await screen.findByLabelText("6-digit code");
    await waitFor(() => expect(field).toBeEnabled());

    fireEvent.change(field, { target: { value: "123" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter all 6 digits.");
    expect(mfa.challengeAndVerify).not.toHaveBeenCalled();

    fireEvent.change(field, { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("That code is not right or has expired."));
    expect(screen.queryByText(/Invalid TOTP/)).toBeNull();
  });

  it("offers a way out", async () => {
    mfa.listFactors.mockResolvedValue(factors([VERIFIED]));
    render(<MfaChallenge />);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(assign).toHaveBeenCalledWith("/login"));
    expect(signOutWorkspace).toHaveBeenCalled();
  });
});

describe("Settings: two-step verification", () => {
  it("is not offered where the API cannot enforce it", () => {
    access.model = { two_step_verification: "unavailable", account_deletion: "unavailable" };
    render(<TherapistSettings section="privacy" />);

    expect(screen.queryByText("Two-step verification")).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete account…" })).toBeNull();
  });

  it("turns on after the first code from the app is confirmed", async () => {
    mfa.listFactors
      .mockResolvedValueOnce(factors([]))
      .mockResolvedValueOnce(factors([{ id: "stale", factor_type: "totp", status: "unverified" }]));
    mfa.enroll.mockResolvedValue({
      data: { id: "factor-new", type: "totp", totp: { qr_code: "data:image/svg+xml;utf-8,<svg/>", secret: "SECRETKEY", uri: "otpauth://x" } },
      error: null,
    });
    mfa.challengeAndVerify.mockResolvedValue({ data: {}, error: null });
    render(<TherapistSettings section="privacy" />);

    fireEvent.click(await screen.findByRole("button", { name: "Turn on" }));

    expect(await screen.findByRole("img", { name: "QR code that adds PasaScope to an authenticator app" })).toHaveAttribute(
      "src",
      "data:image/svg+xml;utf-8,<svg/>",
    );
    expect(screen.getByText("SECRETKEY")).toBeInTheDocument();
    // A half-finished enrollment from before is cleared first.
    expect(mfa.unenroll).toHaveBeenCalledWith({ factorId: "stale" });
    expect(mfa.enroll).toHaveBeenCalledWith({ factorType: "totp", friendlyName: "PasaScope" });

    fireEvent.change(screen.getByLabelText("Code from the app"), { target: { value: "111222" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and turn on" }));

    expect(await screen.findByText("Two-step verification is on.")).toBeInTheDocument();
    expect(mfa.challengeAndVerify).toHaveBeenCalledWith({ factorId: "factor-new", code: "111222" });
    expect(screen.getByRole("button", { name: "Turn off" })).toBeInTheDocument();
  });

  it("turns off after confirmation", async () => {
    mfa.listFactors.mockResolvedValue(factors([VERIFIED]));
    render(<TherapistSettings section="privacy" />);

    fireEvent.click(await screen.findByRole("button", { name: "Turn off" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Turn off" }));

    expect(await screen.findByText("Two-step verification is off.")).toBeInTheDocument();
    expect(mfa.unenroll).toHaveBeenCalledWith({ factorId: "factor-1" });
    expect(auth.refreshSession).toHaveBeenCalled();
  });
});

describe("Settings: deleting the account", () => {
  async function openDialog() {
    mfa.listFactors.mockResolvedValue(factors([]));
    render(<TherapistSettings section="privacy" />);
    fireEvent.click(screen.getByRole("button", { name: "Delete account…" }));
    return screen.getByRole("dialog");
  }

  it("deletes only after the email address is typed, then signs out", async () => {
    deleteOwnAccount.mockResolvedValue(undefined);
    const dialog = await openDialog();
    const confirm = within(dialog).getByRole("button", { name: "Delete account" });
    expect(confirm).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(/To confirm, type your email address/), { target: { value: " AOM@example.test " } });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);

    await waitFor(() => expect(assign).toHaveBeenCalledWith("/login?account=deleted"));
    expect(deleteOwnAccount).toHaveBeenCalledTimes(1);
    expect(signOutWorkspace).toHaveBeenCalled();
  });

  it("says when only the sign-in account is left", async () => {
    const { ApiError } = await import("@/lib/api");
    deleteOwnAccount.mockRejectedValue(new ApiError(502, "{}"));
    const dialog = await openDialog();
    fireEvent.change(within(dialog).getByLabelText(/To confirm/), { target: { value: "aom@example.test" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete account" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Your records were deleted, but the account itself could not be removed yet.");
    expect(assign).not.toHaveBeenCalled();
  });

  it("says nothing was deleted when the request fails", async () => {
    const { ApiError } = await import("@/lib/api");
    deleteOwnAccount.mockRejectedValue(new ApiError(503, "{}"));
    const dialog = await openDialog();
    fireEvent.change(within(dialog).getByLabelText(/To confirm/), { target: { value: "aom@example.test" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete account" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Nothing was deleted.");
  });
});
