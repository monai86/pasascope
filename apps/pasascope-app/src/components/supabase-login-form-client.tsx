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
import { useEffect, useRef, type FormEvent, useState } from "react";

import { type RuntimeSettings } from "@/lib/api";
import {
  buildSupabaseBrowserAuthSnapshotFromSession,
  type SupabaseSessionLike,
} from "@/lib/supabase-browser-auth";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { getSupabaseBrowserClientConfigStatus } from "@/lib/supabase-browser-client-config";
import { classifyAuthError } from "@/lib/supabase-auth-error";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { supabaseLoginMessages } from "@/components/supabase-login.messages";
import { useMessages } from "@/i18n/locale-provider";
import { PASSWORD_MIN_LENGTH } from "@/lib/password-policy";

function resolvePostLoginRoute(role: unknown): string {
  if (role === "org_admin" || role === "platform_operator") {
    return "/settings?scope=admin";
  }

  return "/dashboard";
}

const FOCUS_RING = "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";
// 16px text keeps iOS from zooming the page when a field takes focus.
const FIELD =
  "min-h-12 w-full rounded-control border border-chat-line-strong bg-surface py-2 text-base text-ink outline-none transition placeholder:text-ink-subtle focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] aria-[invalid=true]:border-[color:var(--color-danger-text)] motion-reduce:transition-none";
const PRIMARY = `group inline-flex min-h-[52px] w-full items-center justify-center rounded-full bg-action px-6 font-semibold text-white shadow-chat-action transition hover:bg-action-hover disabled:cursor-not-allowed disabled:bg-chat-line disabled:text-ink-subtle disabled:shadow-none motion-reduce:transition-none ${FOCUS_RING}`;

// The owner's choice (2026-10-13). NIST SP 800-63B-4 asks for 15 where the password
// is the only factor and 8 beside a second one, with no composition rules either way.
// It applies to a new password; an existing one still signs in.
export { PASSWORD_MIN_LENGTH };

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
  const [acknowledged, setAcknowledged] = useState(false);
  // Which sign-up field stopped the form, so its own message can sit beside it.
  const [fieldError, setFieldError] = useState<"password" | "acknowledge" | null>(null);
  const passwordInput = useRef<HTMLInputElement>(null);
  const acknowledgeInput = useRef<HTMLInputElement>(null);

  /** Words for a failed request, in the interface language and without the service's own text. */
  function describe(error: unknown, fallback: string): string {
    const problem = classifyAuthError(error);
    if (problem === "other") return fallback;
    if (problem === "weakPassword") return t.passwordTooShort(PASSWORD_MIN_LENGTH);
    return t.problems[problem];
  }
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

    // Counted in characters as read, so one Thai letter or emoji is one.
    if (Array.from(password).length < PASSWORD_MIN_LENGTH) {
      setFieldError("password");
      passwordInput.current?.focus();
      return;
    }
    if (publicSignup && !acknowledged) {
      setFieldError("acknowledge");
      acknowledgeInput.current?.focus();
      return;
    }
    setFieldError(null);

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
            // When the person confirmed they had read the privacy page.
            privacy_acknowledged_at: publicSignup ? new Date().toISOString() : undefined,
          },
          emailRedirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}${landingPath}`,
        },
      });

      if (error) {
        setErrorMessage(describe(error, t.errors.signUpFailed));
        return;
      }

      if (data.session) {
        publishSupabaseSessionPayload(data.session);
        setStatusMessage(t.status.signUpSignedIn);
        router.push(publicSignup ? landingPath : resolvePostLoginRoute(data.session.user?.app_metadata?.role));
        router.refresh();
      } else {
        setStatusMessage(publicSignup ? t.open.status.signUpConfirmEmail : t.status.signUpConfirmEmail);
      }
    } catch (error) {
      setErrorMessage(describe(error, t.errors.signUpFailed));
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
        setErrorMessage(describe(error, t.errors.signInFailed));
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
      setStatusMessage(publicSignup ? t.open.status.signInAccepted : t.status.signInAccepted);
      router.push(publicSignup ? landingPath : resolvePostLoginRoute(data.session?.user?.app_metadata?.role));
      router.refresh();
    } catch (error) {
      setErrorMessage(describe(error, t.errors.signInFailed));
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
        setErrorMessage(describe(error, t.errors.recoveryFailed));
        return;
      }

      setStatusMessage(publicSignup ? t.open.status.recoverySent : t.status.recoverySent);
    } catch (error) {
      setErrorMessage(describe(error, t.errors.recoveryFailed));
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
    <div className="rounded-panel bg-surface p-6 shadow-chat-card sm:p-8">
      <h2 className="font-display text-2xl font-semibold leading-snug text-ink sm:text-[1.7rem]">
        {publicSignup ? t.open.title : t.title}
      </h2>
      <p className="mb-6 mt-2 leading-relaxed text-ink-muted">
        {publicSignup ? t.open.subtitle : t.subtitle}
      </p>

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

      {/* Sign in or create an account */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex rounded-full bg-chat-frame p-1">
          {(["signin", "signup"] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={mode === option}
              onClick={() => {
                setMode(option);
                setErrorMessage("");
                setStatusMessage("");
                setFieldError(null);
              }}
              className={`min-h-11 rounded-full px-5 text-sm font-semibold transition motion-reduce:transition-none ${FOCUS_RING} ${
                mode === option ? "bg-surface text-ink shadow-chat-card" : "text-ink-subtle hover:text-ink"
              }`}
            >
              {option === "signin" ? t.modes.signIn : t.modes.signUp}
            </button>
          ))}
        </div>
        {publicSignup ? null : <span className="text-xs font-medium text-ink-subtle">{t.modes.invitationOnly}</span>}
      </div>

      {/* Form */}
      <form
        aria-label={t.formLabel}
        onSubmit={mode === "signin" ? handleSignIn : handleSignUp}
        className="space-y-4"
      >
        {mode === "signup" && (
          <label className="block text-sm font-medium text-ink">
            <span className="mb-1.5 flex items-baseline justify-between gap-3">
              {t.displayName}
              <span className="text-xs font-normal text-ink-subtle">{t.optional}</span>
            </span>
            <input
              className={`${FIELD} px-4`}
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
            <label htmlFor="clinical-email-input" className="block text-sm font-medium text-ink">
              {t.email}
            </label>
            {publicSignup ? null : <span className="text-xs text-ink-subtle">{t.emailHint}</span>}
          </div>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
            <input
              id="clinical-email-input"
              className={`${FIELD} pl-11 pr-4`}
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
            <label htmlFor="clinical-password-input" className="block text-sm font-medium text-ink">
              {t.password}
            </label>
            {/* Recovery belongs to an account that exists, so it is not offered while creating one. */}
            {mode === "signin" ? (
              <button
                type="button"
                onClick={handlePasswordRecovery}
                disabled={!browserClient || isSendingRecovery}
                className={`-my-3.5 rounded-control py-3.5 text-xs font-medium text-brand underline-offset-4 transition hover:underline disabled:opacity-50 ${FOCUS_RING}`}
              >
                {isSendingRecovery ? t.sendingRecovery : t.sendRecovery}
              </button>
            ) : null}
          </div>
          <div className="relative">
            <LockKeyhole className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
            <input
              id="clinical-password-input"
              className={`${FIELD} pl-11 pr-12`}
              type={showPassword ? "text" : "password"}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              ref={passwordInput}
              aria-describedby={mode === "signup" ? "clinical-password-hint" : undefined}
              aria-invalid={mode === "signup" && fieldError === "password" ? true : undefined}
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                if (fieldError === "password") setFieldError(null);
              }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className={`absolute right-1 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full text-ink-subtle transition hover:text-ink ${FOCUS_RING}`}
              aria-label={showPassword ? t.hidePassword : t.showPassword}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {mode === "signup" ? (
            // One line that is the rule until the form is stopped by it, then the problem.
            <p
              id="clinical-password-hint"
              role={fieldError === "password" ? "alert" : undefined}
              className={`mt-2 text-[13px] leading-5 ${
                fieldError === "password" ? "font-medium text-[color:var(--color-danger-text)]" : "text-ink-muted"
              }`}
            >
              {fieldError === "password" ? t.passwordTooShort(PASSWORD_MIN_LENGTH) : t.passwordHint(PASSWORD_MIN_LENGTH)}
            </p>
          ) : null}
        </div>

        {mode === "signup" && publicSignup ? (
          <div>
            <label className="flex min-h-11 cursor-pointer items-start gap-3 py-2 text-sm leading-6 text-ink">
              <input
                ref={acknowledgeInput}
                type="checkbox"
                checked={acknowledged}
                aria-describedby={fieldError === "acknowledge" ? "privacy-acknowledge-error" : undefined}
                aria-invalid={fieldError === "acknowledge" ? true : undefined}
                onChange={(event) => {
                  setAcknowledged(event.target.checked);
                  if (fieldError === "acknowledge") setFieldError(null);
                }}
                className={`mt-0.5 h-5 w-5 shrink-0 rounded ${FOCUS_RING}`}
              />
              <span>
                {t.acknowledge.before}
                <Link href="/privacy" target="_blank" className="font-semibold text-brand underline underline-offset-4">
                  {t.acknowledge.link}
                </Link>
                {t.acknowledge.after}
              </span>
            </label>
            {fieldError === "acknowledge" ? (
              <p id="privacy-acknowledge-error" role="alert" className="text-[13px] font-medium leading-5 text-[color:var(--color-danger-text)]">
                {t.acknowledge.required}
              </p>
            ) : null}
          </div>
        ) : null}

        {/* Primary action */}
        <div className="pt-1">
          {mode === "signin" ? (
            <button
              type="submit"
              disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-label={buttonAriaLabel}
              className={PRIMARY}
            >
              <span className="flex items-center justify-center gap-2">
                <span>
                  {isSubmitting
                    ? t.signingIn
                    : publicSignup
                      ? t.open.signIn
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
              className={PRIMARY}
            >
              <span className="flex items-center justify-center gap-2">
                <span>
                  {isSubmitting
                    ? t.creatingAccount
                    : publicSignup
                      ? t.open.createAccount
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
          <div className="w-full border-t border-chat-line" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-surface px-3 text-xs font-medium text-ink-subtle">
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
          className={`inline-flex min-h-[52px] items-center justify-center gap-2.5 rounded-full border border-action-quiet-border bg-surface px-5 text-sm font-semibold text-ink transition hover:bg-action-quiet-hover disabled:opacity-50 motion-reduce:transition-none ${FOCUS_RING}`}
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
        <div className="mt-5 space-y-2 border-t border-chat-line pt-4 text-[13px] leading-5 text-ink-subtle">
          <p>{t.publicNote.stored}</p>
          <p>{t.publicNote.boundary}</p>
          <p><Link href="/privacy" className="font-semibold text-brand underline underline-offset-4">{t.publicNote.privacy}</Link></p>
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
