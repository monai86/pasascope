"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { shellMessages } from "@/components/shell.messages";
import { useMessages } from "@/i18n/locale-provider";
import {
  SUPABASE_ACCESS_SESSION_EVENT,
  type SupabaseAccessSession,
} from "@/lib/supabase-access-session";
import { loadOrRestoreSupabaseAccessSession } from "@/lib/use-supabase-access-session";

// Only accounts with two-step verification see it, so it stays out of every page's bundle.
const MfaChallenge = dynamic(() => import("@/components/mfa-challenge").then((module) => module.MfaChallenge));

/**
 * Opens the workspace for a signed-in account, asks for the authenticator code
 * when the account has two-step verification, and sends anyone else to sign in.
 */
export function SupabaseWorkspaceAccessGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const t = useMessages(shellMessages);
  const [session, setSession] = useState<SupabaseAccessSession | null>(() => {
    if (typeof window === "undefined") return null;
    return loadOrRestoreSupabaseAccessSession();
  });

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

  if (session?.stage === "authenticated") {
    return <>{children}</>;
  }

  if (session?.stage === "mfa_required") {
    return <MfaChallenge email={session.email} />;
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-4 text-center" role="status">
      <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-action" aria-hidden="true" />
      <p className="text-base font-semibold text-ink">{t.signInRedirect}</p>
    </main>
  );
}
