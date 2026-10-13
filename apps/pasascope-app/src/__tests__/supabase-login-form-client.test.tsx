import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { routerPush, routerRefresh } from "@/__tests__/setup";
import { ACCOUNT_NOT_PROVISIONED_MESSAGE, SupabaseLoginFormClient } from "@/components/supabase-login-form-client";
import type { RuntimeSettings } from "@/lib/api";
import { resetSupabaseBrowserClientForTests } from "@/lib/supabase-browser-client";

const signInWithPassword = vi.fn();
const resetPasswordForEmail = vi.fn();
const signUp = vi.fn();

vi.mock("@/lib/supabase-browser-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/supabase-browser-client")>("@/lib/supabase-browser-client");

  return {
    ...actual,
    getSupabaseBrowserClient: () => ({
      auth: {
        signInWithPassword,
        resetPasswordForEmail,
        signUp,
      },
    }),
  };
});

const runtimeSettings: RuntimeSettings = {
  mock_mode: false,
  auth_mode: "supabase",
  model_version: "test-model",
  feature_schema: "test-schema",
  guideline_mapping: "test-guideline-map",
  user_roles: ["therapist", "clinical_supervisor", "org_admin"],
  access_model: {
    invitation_only: true,
    required_app_aal: "aal2",
    active_organization_session: "explicit_selection_when_ambiguous",
    production_mock_mode: "forbidden",
  },
  data_retention: "test-retention",
  consent_policy: "test-consent",
  capabilities: {
    cases: "available",
    audio_upload: "experimental",
    transcription: "experimental",
    transcript_qa: "available",
    feature_extraction: "available",
    ai_review: "disabled",
    report_drafting: "disabled",
    pdf_export: "unavailable",
  },
  pipeline_settings: {
    audio_processing: "test-audio",
    job_queue_mode: "test-queue",
    repository_mode: "test-repository",
    storage_mode: "test-storage",
  },
};

describe("SupabaseLoginFormClient", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    routerPush.mockClear();
    routerRefresh.mockClear();
    signInWithPassword.mockReset();
    resetPasswordForEmail.mockReset();
    signUp.mockReset();
    resetSupabaseBrowserClientForTests();
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://lingualens.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "sb_publishable_test-key");
  });

  it("submits email/password sign-in and routes org admins to settings", async () => {
    const listener = vi.fn();
    signInWithPassword.mockResolvedValue({
      data: {
        session: {
          aal: "aal2",
          user: {
            id: "user_org_admin_001",
            email: "admin@clinic.example",
            app_metadata: {
              role: "org_admin",
              membership_active: true,
              invitation_status: "accepted",
              organization_id: "clinic_001",
            },
          },
        },
      },
      error: null,
    });
    window.addEventListener("pasascope:supabase-session-source", listener as EventListener);

    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@clinic.example" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in with Supabase" }));

    await waitFor(() => {
      expect(signInWithPassword).toHaveBeenCalledWith({
        email: "admin@clinic.example",
        password: "secret-password",
      });
    });
    await waitFor(() => {
      expect(listener).toHaveBeenCalledTimes(1);
      expect(routerPush).toHaveBeenCalledWith("/settings?scope=admin");
      expect(routerRefresh).toHaveBeenCalled();
    });

    window.removeEventListener("pasascope:supabase-session-source", listener as EventListener);
  });

  it("tells an account without an organization membership that it is not provisioned", async () => {
    signInWithPassword.mockResolvedValue({
      data: {
        session: {
          aal: "aal1",
          user: { id: "user_new_001", email: "new.user@clinic.example", app_metadata: {} },
        },
      },
      error: null,
    });

    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new.user@clinic.example" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in with Supabase" }));

    expect(await screen.findByText(ACCOUNT_NOT_PROVISIONED_MESSAGE)).toBeInTheDocument();
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("sends a Supabase password recovery email back to the login route", async () => {
    resetPasswordForEmail.mockResolvedValue({
      error: null,
    });

    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "clinician@clinic.example" } });
    fireEvent.click(screen.getByRole("button", { name: "Send recovery email" }));

    await waitFor(() => {
      expect(resetPasswordForEmail).toHaveBeenCalledWith("clinician@clinic.example", {
        redirectTo: "http://localhost:3000/login",
      });
    });
    expect(await screen.findByText("Recovery email sent. App access still requires accepted membership and AAL2 after reset.")).toBeInTheDocument();
  });

  it("fails closed with an explicit invalid-config status when the browser env is malformed", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://lingualens.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "bad-key");

    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    expect(screen.getByRole("button", { name: "Supabase browser config invalid" })).toBeDisabled();
    expect(
      screen.getByText((content) => content.includes(
        "NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is malformed for the launch contract.",
      )),
    ).toBeInTheDocument();
  });

  it("words the form for a clinic when access is by invitation", () => {
    render(<SupabaseLoginFormClient runtimeSettings={runtimeSettings} />);

    expect(screen.getByRole("heading", { name: "Sign in to the clinic workspace" })).toBeInTheDocument();
    expect(screen.getByText("Clinic email")).toBeInTheDocument();
    expect(screen.getByText("Invitation-only")).toBeInTheDocument();
  });

  it("drops the clinic wording where anyone can sign up", () => {
    const open: RuntimeSettings = {
      ...runtimeSettings,
      access_model: { ...runtimeSettings.access_model, invitation_only: false, public_signup: true, review_gates: "open" },
    } as RuntimeSettings;
    render(<SupabaseLoginFormClient runtimeSettings={open} />);

    expect(screen.getByRole("heading", { name: "Sign in to PasaScope" })).toBeInTheDocument();
    expect(screen.queryByText(/\bclinic\b/i)).toBeNull();
    expect(screen.queryByText("Invitation-only")).toBeNull();

    // One of the two is chosen, and choosing the other asks for a display name.
    expect(screen.getByRole("button", { name: "Sign in", pressed: true })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create account", pressed: false }));
    expect(screen.getByRole("button", { name: "Create account", pressed: true })).toBeInTheDocument();
    expect(screen.getByLabelText(/Display name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Display name/)).toHaveAccessibleName("Display name optional");
  });

  describe("creating an account where anyone can sign up", () => {
    const open: RuntimeSettings = {
      ...runtimeSettings,
      access_model: { ...runtimeSettings.access_model, invitation_only: false, public_signup: true, review_gates: "open" },
    } as RuntimeSettings;
    const LONG_PASSWORD = "four quiet words here";

    function startSignUp(password: string) {
      render(<SupabaseLoginFormClient runtimeSettings={open} />);
      fireEvent.click(screen.getByRole("button", { name: "Create account", pressed: false }));
      fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new.user@example.org" } });
      fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
    }

    it("states the password rule and stops a shorter one before anything is sent", () => {
      startSignUp("short");
      expect(screen.getByLabelText("Password")).toHaveAccessibleDescription(/At least 8 characters/);

      fireEvent.click(screen.getByRole("button", { name: "Create Account" }));

      expect(screen.getByRole("alert")).toHaveTextContent("Use at least 8 characters.");
      expect(screen.getByLabelText("Password")).toHaveAttribute("aria-invalid", "true");
      expect(screen.getByLabelText("Password")).toHaveFocus();
      expect(signUp).not.toHaveBeenCalled();
    });

    it("needs the privacy page acknowledged, and records when it was", async () => {
      signUp.mockResolvedValue({ data: { session: null }, error: null });
      startSignUp(LONG_PASSWORD);

      fireEvent.click(screen.getByRole("button", { name: "Create Account" }));
      expect(screen.getByRole("alert")).toHaveTextContent("Tick the box to confirm you have read it.");
      expect(signUp).not.toHaveBeenCalled();

      const box = screen.getByRole("checkbox", { name: /I have read how PasaScope stores and uses data/ });
      expect(screen.getByRole("link", { name: "how PasaScope stores and uses data" })).toHaveAttribute("href", "/privacy");
      fireEvent.click(box);
      fireEvent.click(screen.getByRole("button", { name: "Create Account" }));

      await waitFor(() => expect(signUp).toHaveBeenCalledTimes(1));
      const sent = signUp.mock.calls[0][0];
      expect(sent.password).toBe(LONG_PASSWORD);
      expect(Date.parse(sent.options.data.privacy_acknowledged_at)).not.toBeNaN();
      expect(await screen.findByText(/Check your inbox/)).toBeInTheDocument();
    });

    it("does not repeat the service's wording or say outright that the email has an account", async () => {
      signUp.mockResolvedValue({
        data: { session: null },
        error: { message: "User already registered", code: "user_already_exists", status: 422 },
      });
      startSignUp(LONG_PASSWORD);
      fireEvent.click(screen.getByRole("checkbox"));
      fireEvent.click(screen.getByRole("button", { name: "Create Account" }));

      expect(await screen.findByRole("alert")).toHaveTextContent(
        "An account could not be created with this email. If it is yours, sign in or send a recovery email.",
      );
      expect(screen.queryByText(/already registered/i)).toBeNull();
    });

    it("words a wrong password and a rate limit in the interface language", async () => {
      signInWithPassword.mockResolvedValueOnce({
        data: { session: null },
        error: { message: "Invalid login credentials", code: "invalid_credentials", status: 400 },
      });
      render(<SupabaseLoginFormClient runtimeSettings={open} />);
      fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.org" } });
      fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
      fireEvent.click(screen.getByRole("button", { name: "Sign in with Supabase" }));
      expect(await screen.findByRole("alert")).toHaveTextContent("The email or password is not right.");

      signInWithPassword.mockResolvedValueOnce({ data: { session: null }, error: { message: "Request rate limit reached", status: 429 } });
      fireEvent.click(screen.getByRole("button", { name: "Sign in with Supabase" }));
      await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Too many attempts. Wait a few minutes and try again."));
    });

    it("does not say whether a recovery email's address has an account", async () => {
      resetPasswordForEmail.mockResolvedValue({ error: null });
      render(<SupabaseLoginFormClient runtimeSettings={open} />);
      fireEvent.change(screen.getByLabelText("Email"), { target: { value: "someone@example.org" } });
      fireEvent.click(screen.getByRole("button", { name: "Send recovery email" }));

      expect(await screen.findByText("If this email has an account, a recovery message is on its way.")).toBeInTheDocument();
    });
  });
});
