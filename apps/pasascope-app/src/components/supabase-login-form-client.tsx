"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  ChevronDown,
  Eye,
  EyeOff,
  LockKeyhole,
  LogIn,
  Mail,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import { useEffect, type FormEvent, useState } from "react";

import { type RuntimeSettings } from "@/lib/api";
import {
  buildSupabaseBrowserAuthSnapshotFromSession,
  type SupabaseSessionLike,
} from "@/lib/supabase-browser-auth";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { getSupabaseBrowserClientConfigStatus } from "@/lib/supabase-browser-client-config";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { supabaseLoginMessages } from "@/components/supabase-login.messages";
import { useMessages } from "@/i18n/locale-provider";

function resolvePostLoginRoute(role: unknown): string {
  if (role === "org_admin" || role === "platform_operator") {
    return "/settings?scope=admin";
  }

  return "/dashboard";
}

export const ACCOUNT_NOT_PROVISIONED_MESSAGE =
  "บัญชีนี้ยังไม่ได้รับสิทธิ์เข้าองค์กรใด กรุณาติดต่อผู้ดูแลองค์กรเพื่อรับคำเชิญ · This account has not been added to an organization yet. Ask your organization admin for an invitation.";

export function SupabaseLoginFormClient({
  runtimeSettings,
}: {
  runtimeSettings: RuntimeSettings;
}) {
  const router = useRouter();
  const supabaseSession = useSupabaseAccessSession();

  useEffect(() => {
    if (supabaseSession?.stage === "authenticated") {
      router.replace(runtimeSettings.access_model?.public_signup === true ? "/today" : resolvePostLoginRoute(supabaseSession.role));
    }
  }, [supabaseSession?.stage, supabaseSession?.role, router, runtimeSettings.access_model?.public_signup]);

  const invitationOnly = runtimeSettings.access_model?.invitation_only !== false;
  const publicSignup = runtimeSettings.access_model?.public_signup === true;
  const landingPath = publicSignup ? "/today" : "/dashboard";
  const browserClientStatus = getSupabaseBrowserClientConfigStatus();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const t = useMessages(supabaseLoginMessages);
  const [roleTab, setRoleTab] = useState<"slp" | "admin" | "parent">("slp");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPolicy, setShowPolicy] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);
  const [isSendingRecovery, setIsSendingRecovery] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const browserClient = browserClientStatus.configured ? getSupabaseBrowserClient() : null;

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Check query params for error
    const searchParams = new URLSearchParams(window.location.search);
    const queryError = searchParams.get("error_description") || searchParams.get("error");

    // Check hash fragment for error or access_token
    let hashError: string | null = null;
    let hashAccessToken: string | null = null;
    if (window.location.hash && window.location.hash.startsWith("#")) {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      hashError = hashParams.get("error_description") || hashParams.get("error");
      hashAccessToken = hashParams.get("access_token");
    }

    const detectedError = queryError || hashError;
    if (detectedError) {
      setErrorMessage(decodeURIComponent(detectedError.replace(/\+/g, " ")));
      return;
    }

    // If OAuth code or access token is in URL on login page, exchange and sync
    const code = searchParams.get("code");
    if (code || hashAccessToken) {
      setIsGoogleSubmitting(true);
      setStatusMessage("กำลังยืนยันข้อมูลการเข้าสู่ระบบ...");
      if (browserClient && code && typeof browserClient.auth?.exchangeCodeForSession === "function") {
        void browserClient.auth.exchangeCodeForSession(code).then(({ data, error }) => {
          if (error) {
            setErrorMessage(error.message);
            setIsGoogleSubmitting(false);
          } else if (data?.session) {
            publishSupabaseSessionPayload(data.session);
            router.replace(landingPath);
          }
        }).catch((err) => {
          setErrorMessage(err instanceof Error ? err.message : "Exchange failed");
          setIsGoogleSubmitting(false);
        });
      }
    }
  }, [browserClient, router, landingPath]);
  const configStatusLabel = browserClientStatus.configured
    ? "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY detected."
    : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
      ? "waiting for NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
      : "NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is malformed for the launch contract.";

  async function handleGoogleSignIn() {
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("ไม่พบการตั้งค่า Supabase บนระบบ (NEXT_PUBLIC_SUPABASE_URL หรือ NEXT_PUBLIC_SUPABASE_ANON_KEY ขาดหายไปใน Vercel Environment Variables)");
      return;
    }

    if (typeof browserClient?.auth?.signInWithOAuth !== "function") {
      setErrorMessage(t.errors.googleUnsupported);
      return;
    }

    setIsGoogleSubmitting(true);

    try {
      const { error } = await browserClient.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}${landingPath}`,
        },
      });

      if (error) {
        if (error.message.toLowerCase().includes("not enabled") || error.message.toLowerCase().includes("not be found")) {
          setErrorMessage(t.errors.googleNotEnabled);
        } else {
          setErrorMessage(error.message);
        }
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t.errors.googleFailed);
    } finally {
      setIsGoogleSubmitting(false);
    }
  }

  async function handleSignUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage(t.errors.configMissing);
      return;
    }

    if (typeof browserClient?.auth?.signUp !== "function") {
      setErrorMessage(t.errors.signUpUnsupported);
      return;
    }

    setIsSubmitting(true);

    try {
      const { data, error } = await browserClient.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: {
            full_name: fullName.trim() || undefined,
            display_name: fullName.trim() || undefined,
            clinical_role: roleTab === "admin" ? "clinic_admin" : roleTab === "parent" ? "parent_guardian" : "therapist_slp",
          },
          emailRedirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}${landingPath}`,
        },
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      if (data.session) {
        publishSupabaseSessionPayload(data.session);
        setStatusMessage(t.status.signUpSignedIn);
        router.push(publicSignup ? landingPath : resolvePostLoginRoute(data.session.user?.app_metadata?.role));
        router.refresh();
      } else {
        setStatusMessage(t.status.signUpConfirmEmail);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t.errors.signUpFailed);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage(t.errors.configMissing);
      return;
    }

    setIsSubmitting(true);

    try {
      const { data, error } = await browserClient.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      if (data.session && !buildSupabaseBrowserAuthSnapshotFromSession(data.session as unknown as SupabaseSessionLike)) {
        // Signed in, but the token carries no organization membership yet.
        await browserClient.auth.signOut?.();
        publishSupabaseSessionPayload(null);
        setErrorMessage(ACCOUNT_NOT_PROVISIONED_MESSAGE);
        return;
      }

      publishSupabaseSessionPayload(data.session ?? null);
      setStatusMessage(t.status.signInAccepted);
      router.push(publicSignup ? landingPath : resolvePostLoginRoute(data.session?.user?.app_metadata?.role));
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t.errors.signInFailed);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePasswordRecovery() {
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage(t.errors.configMissing);
      return;
    }

    if (!email.trim()) {
      setErrorMessage(t.errors.enterEmailFirst);
      return;
    }

    setIsSendingRecovery(true);

    try {
      const { error } = await browserClient.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}/login`,
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      setStatusMessage(t.status.recoverySent);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t.errors.recoveryFailed);
    } finally {
      setIsSendingRecovery(false);
    }
  }

  const buttonAriaLabel = isSubmitting
    ? t.signingIn
    : browserClientStatus.configured
      ? t.signInLabel
      : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
        ? t.configMissing
        : t.configInvalid;

  return (
    <div className="rounded-3xl border border-line bg-white p-6 sm:p-8 lg:p-9 shadow-xl transition-all">
      {/* Header Badge & Security Status */}
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-tint opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-brand"></span>
          </span>
          <h2 className="text-xs font-bold uppercase tracking-wider text-[color:var(--color-success-text)]">
            {t.eyebrow}
          </h2>
          <span className="text-xs text-ink-subtle font-medium hidden sm:inline">
            • {t.eyebrowDetail}
          </span>
        </div>
      </div>

      {/* Main Title & Subtitle */}
      <div className="mb-5">
        <h1 className="text-2xl sm:text-[1.7rem] font-extrabold tracking-tight text-ink leading-snug">
          {t.title}
        </h1>
        <p className="mt-1.5 text-xs sm:text-sm text-ink-muted leading-relaxed">
          {t.subtitle}
        </p>
      </div>

      {/* Role tabs apply only where accounts carry an organization role. */}
      {publicSignup ? null : (
      <div className="mb-5 grid grid-cols-3 gap-1 rounded-xl border border-line bg-surface-muted p-1 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setRoleTab("slp")}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all ${
            roleTab === "slp"
              ? "bg-white text-[color:var(--color-success-text)] shadow-xs font-bold"
              : "text-ink-muted hover:text-ink"
          }`}
        >
          <ShieldCheck size={14} className={roleTab === "slp" ? "text-[color:var(--color-success-text)]" : "text-ink-subtle"} />
          <span>{t.roles.slp}</span>
        </button>
        <button
          type="button"
          onClick={() => setRoleTab("admin")}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all ${
            roleTab === "admin"
              ? "bg-white text-[color:var(--color-success-text)] shadow-xs font-bold"
              : "text-ink-muted hover:text-ink"
          }`}
        >
          <Building2 size={14} className={roleTab === "admin" ? "text-[color:var(--color-success-text)]" : "text-ink-subtle"} />
          <span>{t.roles.admin}</span>
        </button>
        <button
          type="button"
          onClick={() => setRoleTab("parent")}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all ${
            roleTab === "parent"
              ? "bg-white text-[color:var(--color-success-text)] shadow-xs font-bold"
              : "text-ink-muted hover:text-ink"
          }`}
        >
          <span>{t.roles.parent}</span>
        </button>
      </div>
      )}

      {/* Sign-in / Sign-up Mode Selector */}
      <div className="mb-5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setErrorMessage("");
              setStatusMessage("");
            }}
            className={`font-semibold pb-1 border-b-2 transition ${
              mode === "signin"
                ? "border-brand text-ink"
                : "border-transparent text-ink-subtle hover:text-ink-muted"
            }`}
          >
            {t.modes.signIn}
          </button>
          <span className="text-line-strong">|</span>
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setErrorMessage("");
              setStatusMessage("");
            }}
            className={`font-semibold pb-1 border-b-2 transition ${
              mode === "signup"
                ? "border-brand text-ink"
                : "border-transparent text-ink-subtle hover:text-ink-muted"
            }`}
          >
            {t.modes.signUp}
          </button>
        </div>
        {publicSignup ? null : <span className="text-xs text-ink-subtle font-medium">{t.modes.invitationOnly}</span>}
      </div>

      {/* Form */}
      <form
        aria-label={t.formLabel}
        onSubmit={mode === "signin" ? handleSignIn : handleSignUp}
        className="space-y-4"
      >
        {mode === "signup" && (
          <label className="block text-xs font-bold uppercase tracking-wider text-ink">
            <span className="block mb-1.5">
              {t.displayName}
            </span>
            <input
              className="min-h-11 w-full rounded-xl border border-line bg-surface-soft px-3.5 py-2 text-sm text-ink placeholder:text-ink-subtle focus:bg-white focus:border-brand focus:ring-2 focus:ring-[color:var(--color-focus-ring)] outline-none transition"
              type="text"
              autoComplete="name"
              placeholder={t.displayNamePlaceholder}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </label>
        )}

        {/* Email Field with exact accessible name "Email" for test assertions */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="clinical-email-input" className="block text-xs font-bold uppercase tracking-wider text-ink">
              {t.email}
            </label>
            <span className="text-xs font-normal text-ink-subtle normal-case">
              Clinic Email or SLP License ID / อีเมลหรือเลขที่ใบอนุญาต
            </span>
          </div>
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-subtle pointer-events-none" />
            <input
              id="clinical-email-input"
              className="min-h-11 w-full rounded-xl border border-line bg-surface-soft pl-10 pr-3.5 py-2 text-sm text-ink placeholder:text-ink-subtle focus:bg-white focus:border-brand focus:ring-2 focus:ring-[color:var(--color-focus-ring)] outline-none transition font-sans"
              type="email"
              inputMode="email"
              autoComplete="username"
              placeholder="name@example.org"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
        </div>

        {/* Password Field with exact accessible name "Password" for test assertions */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="clinical-password-input" className="block text-xs font-bold uppercase tracking-wider text-ink">
              {t.password}
            </label>
            <button
              type="button"
              onClick={handlePasswordRecovery}
              disabled={!browserClient || isSendingRecovery}
              className="text-xs font-medium text-[color:var(--color-success-text)] hover:text-[color:var(--color-success-text)] hover:underline transition disabled:opacity-50"
            >
              {isSendingRecovery ? t.sendingRecovery : t.sendRecovery}
            </button>
          </div>
          <div className="relative">
            <LockKeyhole className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-subtle pointer-events-none" />
            <input
              id="clinical-password-input"
              className="min-h-11 w-full rounded-xl border border-line bg-surface-soft pl-10 pr-10 py-2 text-sm text-ink placeholder:text-ink-subtle focus:bg-white focus:border-brand focus:ring-2 focus:ring-[color:var(--color-focus-ring)] outline-none transition font-sans"
              type={showPassword ? "text" : "password"}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              placeholder="••••••••••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-ink-subtle hover:text-ink transition"
              aria-label={showPassword ? t.hidePassword : t.showPassword}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {/* Primary action */}
        <div className="pt-1">
          {mode === "signin" ? (
            <button
              type="submit"
              disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-label={buttonAriaLabel}
              className="group relative inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-hover active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-ink-muted disabled:shadow-none"
            >
              <span className="flex items-center justify-center gap-2">
                <span>
                  {isSubmitting
                    ? t.signingIn
                    : t.signIn}
                </span>
                <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" />
              </span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-label={isSubmitting ? t.creatingAccount : t.createAccountLabel}
              className="group relative inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand px-5 py-3 text-sm font-bold text-white shadow-lg transition hover:bg-brand-hover active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-ink-muted"
            >
              <span className="flex items-center justify-center gap-2">
                <span>
                  {isSubmitting
                    ? t.creatingAccount
                    : t.createAccount}
                </span>
                <UserPlus size={17} />
              </span>
            </button>
          )}
        </div>

        {/* Error and Status messages */}
        {errorMessage ? (
          <p className="rounded-xl border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-3.5 py-2.5 text-xs font-medium text-[color:var(--color-danger-text)] leading-relaxed" role="alert">
            {errorMessage}
          </p>
        ) : null}

        {statusMessage ? (
          <p className="rounded-xl border border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] px-3.5 py-2.5 text-xs font-medium text-[color:var(--color-success-text)] leading-relaxed" aria-live="polite">
            {statusMessage}
          </p>
        ) : null}
      </form>

      {/* Divider */}
      <div className="relative my-6 text-center">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-line" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-white px-3 text-xs font-semibold uppercase tracking-wider text-ink-subtle">
            {t.orContinueWith}
          </span>
        </div>
      </div>

      {/* SSO Buttons */}
      <div className="grid grid-cols-1 gap-2.5">
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={isGoogleSubmitting || isSubmitting}
          className="inline-flex min-h-11 items-center justify-center gap-2.5 rounded-xl border border-line bg-white px-3.5 py-2 text-xs font-semibold text-ink shadow-2xs transition hover:bg-surface-soft hover:border-line-strong disabled:opacity-50"
        >
          <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              fill="#EA4335"
            />
          </svg>
          <span>
            {isGoogleSubmitting ? t.connectingGoogle : t.continueWithGoogle}
          </span>
        </button>
      </div>

      {publicSignup ? (
        <div className="mt-4 space-y-2 border-t border-line pt-3 text-xs leading-relaxed text-ink-muted">
          <p>{t.publicNote.stored}</p>
          <p>{t.publicNote.boundary}</p>
          <p><Link href="/privacy" className="font-semibold text-brand underline">{t.publicNote.privacy}</Link></p>
        </div>
      ) : (
      <div className="mt-4 pt-3 border-t border-line">
        <button
          type="button"
          onClick={() => setShowPolicy(!showPolicy)}
          className="flex min-h-10 w-full items-center justify-between text-xs font-semibold text-ink-muted hover:text-ink transition"
        >
          <span className="flex items-center gap-1.5">
            <ShieldCheck size={13} className="text-[color:var(--color-success-text)]" />
            {t.policyToggle}
          </span>
          <ChevronDown
            size={14}
            className={`transition-transform duration-200 ${showPolicy ? "rotate-180" : ""}`}
          />
        </button>

        <div className={`mt-3 space-y-2 text-xs leading-relaxed text-ink-muted ${showPolicy ? "block" : "sr-only sm:not-sr-only"}`}>
          <div className="rounded-xl border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-[color:var(--color-warning-text)]">
            <p className="font-semibold text-xs uppercase tracking-wider text-[color:var(--color-warning-text)]">
              {t.policy.invitationTitle}
            </p>
            <p className="mt-0.5 text-xs">
              {invitationOnly
                ? t.policy.invitationOn
                : t.policy.invitationOff}
            </p>
          </div>

          <div className="rounded-xl border border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] p-3 text-[color:var(--color-success-text)]">
            <p className="font-semibold text-xs uppercase tracking-wider text-[color:var(--color-success-text)]">
              {t.policy.mfaTitle}
            </p>
            <p className="mt-0.5 text-xs">
              {t.policy.mfaBefore} <strong>aal1</strong> {t.policy.mfaMiddle} <strong>aal2</strong> {t.policy.mfaAfter}
            </p>
          </div>

          <div className="rounded-xl border border-line bg-surface-soft p-3 text-ink">
            <p className="font-semibold text-xs uppercase tracking-wider text-ink">
              {t.policy.organizationTitle}
            </p>
            <p className="mt-0.5 text-xs">
              {t.policy.organizationBody}
            </p>
          </div>

          <div className="rounded-xl border border-line bg-white p-3 text-ink-muted">
            <p className="font-semibold text-xs uppercase tracking-wider text-ink">
              {t.policy.recoveryTitle}
            </p>
            <p className="mt-0.5 text-xs">
              {t.policy.recoveryBody}
            </p>
            <p className="mt-1 text-xs">
              {t.policy.runtimeBody}
            </p>
            <p className="mt-1 text-xs font-mono text-ink-subtle">
              {t.policy.browserConfig(configStatusLabel)}
            </p>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
