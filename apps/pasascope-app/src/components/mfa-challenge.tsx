"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ShieldCheck } from "lucide-react";

import { mfaChallengeMessages } from "@/components/mfa-challenge.messages";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useMessages } from "@/i18n/locale-provider";
import { loadVerifiedTotpFactor, normalizeCode, verifyTotpCode, type TotpFactor } from "@/lib/supabase-mfa";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";

/**
 * The second step of signing in. The workspace stays closed until the code
 * from the account's authenticator app raises the session to aal2.
 */
export function MfaChallenge({ email }: { email?: string }) {
  const t = useMessages(mfaChallengeMessages);
  const [factor, setFactor] = useState<TotpFactor | null | undefined>(undefined);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let current = true;
    loadVerifiedTotpFactor()
      .then((found) => {
        if (!current) return;
        setFactor(found);
        if (!found) setError(t.noFactor);
      })
      .catch(() => {
        if (current) setError(t.failed);
      });
    return () => {
      current = false;
    };
    // The lookup runs once; a language change must not repeat it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!factor) return;
    if (code.length !== 6) {
      setError(t.incomplete);
      input.current?.focus();
      return;
    }
    setBusy(true);
    setError("");
    const outcome = await verifyTotpCode(factor.id, code);
    if (outcome === "verified") return;
    setBusy(false);
    setCode("");
    setError(outcome === "wrongCode" ? t.wrongCode : t.failed);
    input.current?.focus();
  }

  async function signOut() {
    await signOutSupabaseWorkspace();
    window.location.assign("/login");
  }

  return (
    <main className="chat-canvas flex min-h-dvh items-center justify-center px-4 py-10 text-ink">
      <section aria-labelledby="mfa-challenge-title" className="w-full max-w-md rounded-panel bg-surface p-6 shadow-chat-card sm:p-8">
        <PasaScopeLogo size="sm" showSubtitle={false} />
        <div className="mt-6 flex items-start gap-3">
          <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-soft text-brand">
            <ShieldCheck size={20} />
          </span>
          <div className="min-w-0">
            <h1 id="mfa-challenge-title" className="font-display text-2xl font-semibold leading-snug text-ink">{t.title}</h1>
            {email ? <p className="mt-1 truncate text-sm text-ink-subtle">{email}</p> : null}
          </div>
        </div>
        <p className="mt-4 leading-relaxed text-ink-muted">{t.body}</p>

        <form onSubmit={submit} className="mt-6 grid gap-4" noValidate>
          <Field label={t.codeLabel} error={error || undefined}>
            {(control) => (
              <Input
                {...control}
                ref={input}
                value={code}
                onChange={(event) => {
                  setCode(normalizeCode(event.target.value));
                  if (error) setError("");
                }}
                inputMode="numeric"
                autoComplete="one-time-code"
                autoFocus
                maxLength={7}
                className="min-h-12 text-center font-mono text-xl tracking-[0.4em]"
                disabled={busy || factor === null}
              />
            )}
          </Field>
          <Button type="submit" size="lg" loading={busy} disabled={busy || !factor}>
            {busy ? t.verifying : t.verify}
          </Button>
        </form>

        <p className="mt-5 text-[13px] leading-5 text-ink-muted">{t.lostApp}</p>
        <Button variant="ghost" className="mt-3" onClick={() => void signOut()}>{t.signOut}</Button>
      </section>
    </main>
  );
}
