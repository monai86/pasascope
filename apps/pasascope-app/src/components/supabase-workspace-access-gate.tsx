"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Building2, Loader2, LockKeyhole, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { SupabaseMfaPanel } from "@/components/supabase-mfa-panel";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import {
  SUPABASE_ACCESS_SESSION_EVENT,
  type SupabaseAccessSession,
} from "@/lib/supabase-access-session";
import { selectSupabaseBrowserOrganization } from "@/lib/supabase-browser-auth";
import { loadOrRestoreSupabaseAccessSession } from "@/lib/use-supabase-access-session";

export function SupabaseWorkspaceAccessGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [session, setSession] = useState<SupabaseAccessSession | null>(() => {
    if (typeof window === "undefined") return null;
    return loadOrRestoreSupabaseAccessSession();
  });
  const [pendingOrganizationId, setPendingOrganizationId] = useState("");
  const availableOrganizationIds = session?.availableOrganizations
    ?.map((option) => option.organizationId)
    .join("|");

  useEffect(() => {
    const syncSession = () => setSession(loadOrRestoreSupabaseAccessSession());
    syncSession();
    window.addEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
    return () => window.removeEventListener(SUPABASE_ACCESS_SESSION_EVENT, syncSession);
  }, []);

  useEffect(() => {
    if (!session || session.stage === "signed_out") {
      router.replace("/login");
    }
  }, [session, router]);

  useEffect(() => {
    if (session?.stage !== "org_selection_required") {
      setPendingOrganizationId("");
      return;
    }

    const nextSelection = session.suggestedOrganizationId
      ?? session.organizationId
      ?? "";
    setPendingOrganizationId(nextSelection);
  }, [
    session?.stage,
    session?.suggestedOrganizationId,
    session?.organizationId,
    availableOrganizationIds,
  ]);

  if (session?.stage === "authenticated" && session.organizationId) {
    return <>{children}</>;
  }

  if (session?.stage === "org_selection_required" && session.availableOrganizations?.length) {
    const suggestedOrganization = session.availableOrganizations.find(
      (option) => option.organizationId === session.suggestedOrganizationId,
    );

    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-[1.25rem] border border-line bg-white p-6 sm:p-8 shadow-soft">
          <div className="mb-6">
            <PasaScopeLogo size="md" />
          </div>
          <p className="inline-flex min-h-8 items-center rounded-full border border-brand-border bg-brand-soft px-3 text-xs font-semibold text-brand">
            Organization selection required
          </p>
          <h1 className="mt-4 text-2xl font-bold tracking-[-0.03em] text-ink sm:text-3xl">Choose an active organization</h1>
          <p className="mt-3 text-sm leading-6 text-ink-muted">
            This account has multiple active memberships. Exactly one organization must be selected before clinical or
            admin workflows can continue.
          </p>

          {suggestedOrganization ? (
            <div className="mt-5 rounded-panel border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-4 text-sm text-[color:var(--color-warning-text)]">
              <p className="font-semibold">Last active organization hint</p>
              <p className="mt-1">
                The previous session used <strong>{suggestedOrganization.label}</strong>. This is a hint only. Review
                the selection and confirm before the workspace opens.
              </p>
            </div>
          ) : null}

          <label className="mt-6 grid gap-2 text-sm font-medium text-ink">
            Active organization
            <select
              aria-label="Select active organization"
              className="min-h-11 rounded-full border border-line bg-white px-4 text-sm text-ink outline-none focus:ring-2 focus:ring-brand"
              value={pendingOrganizationId}
              onChange={(event) => setPendingOrganizationId(event.target.value)}
            >
              <option value="" disabled>Select one organization</option>
              {session.availableOrganizations.map((option) => (
                <option key={option.organizationId} value={option.organizationId}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              className="inline-flex min-h-11 items-center justify-center rounded-full bg-brand px-5 text-sm font-semibold text-white transition hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!pendingOrganizationId}
              onClick={() => {
                if (!pendingOrganizationId) return;
                selectSupabaseBrowserOrganization(pendingOrganizationId);
              }}
            >
              Continue with selected organization
            </button>
          </div>

          <div className="mt-5 rounded-panel border border-line bg-surface-soft p-4 text-sm text-ink-muted">
            <div className="flex items-start gap-3">
              <Building2 size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-brand" />
              <div>
                <p className="font-semibold text-ink">Launch rule</p>
                <p className="mt-1">
                  Organization memory is a hint only. When membership context is ambiguous, selection must be explicit.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (session?.stage === "mfa_required") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-[1.25rem] border border-line bg-white p-6 sm:p-8 shadow-soft">
          <div className="mb-6">
            <PasaScopeLogo size="md" />
          </div>
          <p className="inline-flex min-h-8 items-center rounded-full border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 text-xs font-semibold text-[color:var(--color-warning-text)]">
            AAL1 session detected
          </p>
          <h1 className="mt-4 text-2xl font-bold tracking-[-0.03em] text-ink sm:text-3xl">Additional verification required</h1>
          <p className="mt-3 text-sm leading-6 text-ink-muted">
            Authentication has not yet reached <strong>aal2</strong>. The workspace remains blocked until TOTP MFA is
            completed and the app receives an elevated session.
          </p>

          <div className="mt-5 rounded-panel border border-brand-border bg-brand-soft p-4 text-sm text-brand">
            <div className="flex items-start gap-3">
              <LockKeyhole size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold text-ink">MFA requirement</p>
                <p className="mt-1 text-ink-muted">
                  `aal1` may reach MFA screens only. `aal2` is required before case, report, or admin access.
                </p>
              </div>
            </div>
          </div>

          <p className="mt-5 text-sm leading-6 text-ink-muted">
            Invitation-only onboarding still fails closed. Complete the Supabase TOTP step below to elevate this
            session to <strong>aal2</strong>.
          </p>

          <SupabaseMfaPanel email={session?.email} />
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
      <section className="w-full rounded-[1.25rem] border border-line bg-white p-6 sm:p-8 shadow-soft">
        <div className="mb-6">
          <PasaScopeLogo size="md" />
        </div>
        <p className="inline-flex min-h-8 items-center rounded-full border border-line bg-surface-soft px-3 text-xs font-semibold text-ink-muted">
          Sign-in required
        </p>
        <h1 className="mt-4 text-2xl font-bold tracking-[-0.03em] text-ink sm:text-3xl">Workspace access is blocked</h1>
        <p className="mt-3 text-sm leading-6 text-ink-muted">
          This runtime expects Supabase authentication. Public signup is off, invitation acceptance is required, and no
          workspace route should open before a valid `aal2` session is established.
        </p>

        <div className="mt-5 rounded-panel border border-brand-border bg-brand-soft p-4 text-sm text-brand">
          <div className="flex items-start gap-3">
            <Loader2 size={18} aria-hidden="true" className="mt-0.5 shrink-0 animate-spin" />
            <div>
              <p className="font-semibold text-ink">Redirecting to login portal...</p>
              <p className="mt-1 text-ink-muted">
                Authentication is required to access workspace routes. Automatically taking you to the sign-in page.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center justify-center rounded-full bg-brand px-5 text-sm font-semibold text-white transition hover:bg-brand-hover"
          >
            Go to login
          </Link>
        </div>
      </section>
    </main>
  );
}
