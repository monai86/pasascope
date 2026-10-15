"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { accountSecurityMessages } from "@/features/settings/account-security.messages";
import { FormStatus, Note, Row, Value } from "@/features/settings/components/settings-rows";
import { useMessages } from "@/i18n/locale-provider";
import {
  abandonTotpEnrollment,
  loadVerifiedTotpFactor,
  normalizeCode,
  removeTotpFactor,
  startTotpEnrollment,
  verifyTotpCode,
  type Enrollment,
  type TotpFactor,
} from "@/lib/supabase-mfa";

type State =
  | { kind: "loading" }
  | { kind: "unknown" }
  | { kind: "off" }
  | { kind: "enrolling"; enrollment: Enrollment }
  | { kind: "on"; factor: TotpFactor };

/** Turns two-step verification with an authenticator app on and off. */
export function TwoStepSettings() {
  const t = useMessages(accountSecurityMessages).twoStep;
  const [state, setState] = useState<State>({ kind: "loading" });
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  const [confirmOff, setConfirmOff] = useState(false);

  useEffect(() => {
    let current = true;
    loadVerifiedTotpFactor()
      .then((factor) => current && setState(factor ? { kind: "on", factor } : { kind: "off" }))
      .catch(() => current && setState({ kind: "unknown" }));
    return () => {
      current = false;
    };
  }, []);

  async function turnOn() {
    setBusy(true);
    setError("");
    setDone("");
    try {
      setState({ kind: "enrolling", enrollment: await startTotpEnrollment() });
      setCode("");
    } catch {
      setError(t.failed);
    } finally {
      setBusy(false);
    }
  }

  async function confirm(event: FormEvent) {
    event.preventDefault();
    if (state.kind !== "enrolling") return;
    if (code.length !== 6) return setError(t.incomplete);
    setBusy(true);
    setError("");
    const outcome = await verifyTotpCode(state.enrollment.factorId, code);
    setBusy(false);
    if (outcome === "verified") {
      setState({ kind: "on", factor: { id: state.enrollment.factorId } });
      setDone(t.turnedOn);
      return;
    }
    setCode("");
    setError(outcome === "wrongCode" ? t.wrongCode : t.failed);
  }

  async function cancel() {
    if (state.kind !== "enrolling") return;
    setBusy(true);
    await abandonTotpEnrollment(state.enrollment.factorId);
    setBusy(false);
    setError("");
    setState({ kind: "off" });
  }

  async function turnOff() {
    if (state.kind !== "on") return;
    setBusy(true);
    const removed = await removeTotpFactor(state.factor.id);
    setBusy(false);
    setConfirmOff(false);
    if (!removed) return setError(t.failed);
    setError("");
    setDone(t.turnedOff);
    setState({ kind: "off" });
  }

  if (state.kind === "enrolling") {
    return (
      <Row label={t.title} hint={t.keepApp} align="top">
        <form onSubmit={confirm} className="grid max-w-sm gap-4" noValidate aria-label={t.title}>
          <p className="text-sm leading-6 text-ink">{t.scan}</p>
          {/* A data URL made in the browser; it must not go through an image optimizer. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={state.enrollment.qrCode} alt={t.qrAlt} className="h-44 w-44 rounded-card border border-line bg-white p-2" />
          <div className="grid gap-1">
            <p className="text-[13px] leading-5 text-ink-muted">{t.manual}</p>
            <code className="select-all break-all rounded-control bg-surface-muted px-3 py-2 font-mono text-sm text-ink">
              {state.enrollment.secret}
            </code>
          </div>
          <Field label={t.codeLabel} error={error || undefined}>
            {(control) => (
              <Input
                {...control}
                value={code}
                onChange={(event) => {
                  setCode(normalizeCode(event.target.value));
                  if (error) setError("");
                }}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={7}
                className="max-w-[12rem] font-mono tracking-[0.3em]"
                disabled={busy}
              />
            )}
          </Field>
          <div className="flex flex-wrap gap-3">
            <Button type="submit" variant="secondary" loading={busy} disabled={busy}>
              {busy ? t.confirming : t.confirm}
            </Button>
            <Button variant="ghost" onClick={() => void cancel()} disabled={busy}>{t.cancel}</Button>
          </div>
        </form>
      </Row>
    );
  }

  return (
    <Row label={t.title} hint={t.hint}>
      <div className="grid justify-items-start gap-2">
        {state.kind === "loading" ? <Note>{t.loading}</Note> : null}
        {state.kind === "unknown" ? <Note>{t.failed}</Note> : null}
        {state.kind === "on" ? (
          <>
            <Value>{t.on}</Value>
            <Button variant="secondary" onClick={() => setConfirmOff(true)} disabled={busy}>{t.turnOff}</Button>
          </>
        ) : null}
        {state.kind === "off" ? (
          <>
            <Value>{t.off}</Value>
            <Button variant="secondary" onClick={() => void turnOn()} loading={busy} disabled={busy}>
              {busy ? t.starting : t.turnOn}
            </Button>
          </>
        ) : null}
        <FormStatus status={error ? { kind: "error", message: error } : done ? { kind: "saved", message: done } : { kind: "idle" }} />
      </div>
      <ConfirmDialog
        open={confirmOff}
        title={t.offTitle}
        description={t.offBody}
        confirmLabel={t.turnOff}
        cancelLabel={t.cancel}
        busy={busy}
        onConfirm={() => void turnOff()}
        onCancel={() => setConfirmOff(false)}
      />
    </Row>
  );
}
