"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useLanguageSwitch } from "@/components/language-toggle";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SegmentedControl } from "@/components/ui/segmented-control";
import type { SettingsSection } from "@/features/settings/services/settings-access";
import { settingsMessages } from "@/features/settings/settings.messages";
import type { Locale } from "@/i18n/config";
import { useMessages } from "@/i18n/locale-provider";
import { useAppMode } from "@/lib/app-mode";
import { useConfirmedRuntimeSettings } from "@/lib/confirmed-runtime-settings";
import { PASSWORD_MIN_LENGTH } from "@/lib/password-policy";
import { usePreferences } from "@/lib/preferences";
import { useSafetyCopy } from "@/lib/safety-copy";
import { classifyAuthError } from "@/lib/supabase-auth-error";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

export function TherapistSettings({ section }: { section: SettingsSection }) {
  const t = useMessages(settingsMessages);
  return (
    <section aria-labelledby="settings-section-title" className="rounded-panel border border-line bg-surface px-5 py-6 sm:px-8 sm:py-7">
      <h2 id="settings-section-title" className="text-xl font-semibold text-ink">{t.sections[section]}</h2>
      <p className="mt-1 max-w-[62ch] text-sm leading-6 text-ink-muted">{t.descriptions[section]}</p>
      <div className="mt-6 border-t border-line">
        {section === "account" ? <AccountSettings /> : null}
        {section === "display" ? <DisplaySettings /> : null}
        {section === "workflow" ? <WorkflowSettings /> : null}
        {section === "privacy" ? <PrivacySettings /> : null}
        {section === "help" ? <HelpSettings /> : null}
      </div>
    </section>
  );
}

/** Whether this deployment signs people in with real accounts. */
function useSignedInAccounts(): boolean {
  return useConfirmedRuntimeSettings()?.auth_mode === "supabase";
}

function AccountSettings() {
  const t = useMessages(settingsMessages).account;
  const signedIn = useSignedInAccounts();
  const session = useSupabaseAccessSession();
  const currentName = signedIn ? session?.displayName ?? "" : t.localName;
  const [name, setName] = useState(currentName);
  const [status, setStatus] = useState<{ kind: "idle" | "saving" | "saved" | "error"; message?: string }>({ kind: "idle" });

  // The session arrives after the first render; start from it once it does.
  useEffect(() => {
    setName(currentName);
  }, [currentName]);

  async function saveName(event: FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return setStatus({ kind: "error", message: t.nameEmpty });
    if (trimmed === currentName) return setStatus({ kind: "idle" });
    const client = getSupabaseBrowserClient();
    if (!client) return setStatus({ kind: "error", message: t.failed });
    setStatus({ kind: "saving" });
    const { error } = await client.auth.updateUser({ data: { display_name: trimmed } });
    setStatus(error ? { kind: "error", message: t.failed } : { kind: "saved", message: t.saved });
  }

  if (!signedIn) {
    return (
      <>
        <Row label={t.name}><Value>{t.localName}</Value></Row>
        <Row label={t.workspace}><Value>{t.workspaceValue}</Value></Row>
        <Row label=""><Note>{t.localOnly}</Note></Row>
      </>
    );
  }

  return (
    <>
      <Row label={t.name} hint={t.nameHint} labelFor="settings-display-name">
        <form onSubmit={saveName} className="grid gap-2" noValidate>
          <div className="flex flex-wrap items-center gap-3">
            <Input
              id="settings-display-name"
              aria-label={t.name}
              aria-invalid={status.kind === "error" ? true : undefined}
              aria-describedby={status.kind === "error" ? "settings-display-name-error" : undefined}
              className="max-w-sm flex-1 basis-56"
              value={name}
              maxLength={80}
              autoComplete="name"
              onChange={(event) => {
                setName(event.target.value);
                if (status.kind !== "saving") setStatus({ kind: "idle" });
              }}
            />
            <Button type="submit" variant="secondary" loading={status.kind === "saving"} disabled={status.kind === "saving"}>
              {status.kind === "saving" ? t.saving : t.save}
            </Button>
          </div>
          <FormStatus status={status} errorId="settings-display-name-error" />
        </form>
      </Row>
      <Row label={t.email}><Value>{session?.email ?? t.fallbackName}</Value></Row>
      <Row label={t.workspace}><Value>{t.workspaceValue}</Value></Row>
    </>
  );
}

function DisplaySettings() {
  const copy = useMessages(settingsMessages).display;
  const { locale, change } = useLanguageSwitch();
  const [preferences, update] = usePreferences();

  return (
    <>
      <Row label={copy.language}>
        <SegmentedControl<Locale>
          label={copy.language}
          value={locale}
          onChange={change}
          options={[
            { value: "th", label: "ไทย" },
            { value: "en", label: "English" },
          ]}
        />
      </Row>
      <Row label={copy.textSize}>
        <SegmentedControl<"standard" | "large">
          label={copy.textSize}
          value={preferences.textSize}
          onChange={(value) => update("textSize", value)}
          options={[
            { value: "standard", label: copy.standard },
            { value: "large", label: copy.large },
          ]}
        />
      </Row>
      <Row label={copy.motion} hint={copy.motionHint}>
        <SegmentedControl<"system" | "reduce">
          label={copy.motion}
          value={preferences.motion}
          onChange={(value) => update("motion", value)}
          options={[
            { value: "system", label: copy.followDevice },
            { value: "reduce", label: copy.reduce },
          ]}
        />
      </Row>
    </>
  );
}

function WorkflowSettings() {
  const copy = useMessages(settingsMessages).workflow;
  const [preferences, update] = usePreferences();
  const { externalTranscription } = useAppMode();

  return (
    <>
      <Row label={copy.caseLanguage} hint={copy.caseLanguageHint}>
        <SegmentedControl<"Thai" | "English">
          label={copy.caseLanguage}
          value={preferences.caseLanguage}
          onChange={(value) => update("caseLanguage", value)}
          options={[
            { value: "Thai", label: copy.thai },
            { value: "English", label: copy.english },
          ]}
        />
      </Row>
      <Group title={copy.facts}>
        <Row label={copy.transcription}>
          <Value>{externalTranscription ? copy.transcriptionExternal : copy.transcriptionLocal}</Value>
        </Row>
        <Row label={copy.review}><Value>{copy.reviewValue}</Value></Row>
        <Row label={copy.sharing}><Value>{copy.sharingValue}</Value></Row>
      </Group>
    </>
  );
}

function PrivacySettings() {
  const t = useMessages(settingsMessages).privacy;
  const signedIn = useSignedInAccounts();

  return (
    <>
      {signedIn ? (
        <>
          <ChangePassword />
          <SignOutEverywhere />
        </>
      ) : (
        <Row label={t.passwordTitle}><Note>{t.localOnly}</Note></Row>
      )}
      <Group title={t.dataTitle}>
        {t.dataLines.map(([label, value]) => (
          <Row key={label} label={label}><Value>{value}</Value></Row>
        ))}
      </Group>
      <TextLink href="/privacy">{t.privacyPage}</TextLink>
    </>
  );
}

function ChangePassword() {
  const t = useMessages(settingsMessages).privacy;
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [status, setStatus] = useState<{ kind: "idle" | "saving" | "saved" | "error"; field?: "password" | "confirmation"; message?: string }>({ kind: "idle" });

  async function submit(event: FormEvent) {
    event.preventDefault();
    // Counted as written, the same rule as when the account was created.
    if (Array.from(password).length < PASSWORD_MIN_LENGTH) {
      return setStatus({ kind: "error", field: "password", message: t.tooShort(PASSWORD_MIN_LENGTH) });
    }
    if (password !== confirmation) {
      return setStatus({ kind: "error", field: "confirmation", message: t.mismatch });
    }
    const client = getSupabaseBrowserClient();
    if (!client) return setStatus({ kind: "error", message: t.failed });
    setStatus({ kind: "saving" });
    const { error } = await client.auth.updateUser({ password });
    if (error) {
      const code = (error as { code?: unknown }).code;
      const message = code === "same_password"
        ? t.samePassword
        : classifyAuthError(error) === "weakPassword"
          ? t.tooShort(PASSWORD_MIN_LENGTH)
          : t.failed;
      return setStatus({ kind: "error", field: "password", message });
    }
    setPassword("");
    setConfirmation("");
    setStatus({ kind: "saved", message: t.changed });
  }

  const fieldError = (field: "password" | "confirmation") =>
    status.kind === "error" && status.field === field ? status.message : undefined;

  return (
    <Row label={t.passwordTitle} hint={t.passwordBody} align="top">
      <form onSubmit={submit} className="grid max-w-sm gap-4" noValidate aria-label={t.passwordTitle}>
        <Field label={t.newPassword} hint={t.passwordHint(PASSWORD_MIN_LENGTH)} error={fieldError("password")}>
          {(control) => (
            <Input
              {...control}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          )}
        </Field>
        <Field label={t.confirmPassword} error={fieldError("confirmation")}>
          {(control) => (
            <Input
              {...control}
              type="password"
              autoComplete="new-password"
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
            />
          )}
        </Field>
        <div className="grid gap-2 justify-items-start">
          <Button type="submit" variant="secondary" loading={status.kind === "saving"} disabled={status.kind === "saving"}>
            {status.kind === "saving" ? t.changing : t.change}
          </Button>
          <FormStatus status={status.field ? { kind: "idle" } : status} />
        </div>
      </form>
    </Row>
  );
}

function SignOutEverywhere() {
  const t = useMessages(settingsMessages).privacy;
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function signOutEverywhere() {
    const client = getSupabaseBrowserClient();
    setBusy(true);
    setFailed(false);
    const result = client ? await client.auth.signOut({ scope: "global" }).catch((error: unknown) => ({ error })) : null;
    if (!client || result?.error) {
      setBusy(false);
      setFailed(true);
      return;
    }
    await signOutSupabaseWorkspace();
    router.replace("/login");
  }

  return (
    <Row label={t.everywhereTitle} hint={t.everywhereBody}>
      <div className="grid gap-2 justify-items-start">
        <Button variant="secondary" onClick={signOutEverywhere} loading={busy} disabled={busy}>
          {busy ? t.everywhereBusy : t.everywhereButton}
        </Button>
        {failed ? <p role="alert" className="text-sm font-medium text-[color:var(--color-danger-text)]">{t.everywhereFailed}</p> : null}
      </div>
    </Row>
  );
}

function HelpSettings() {
  const t = useMessages(settingsMessages).help;
  const safety = useSafetyCopy();
  return (
    <>
      {t.lines.map(([label, value]) => (
        // The clinical boundary line shows the registered safety label.
        <Row key={label} label={label}><Value>{value || safety.DECISION_SUPPORT_ONLY_LABEL}</Value></Row>
      ))}
      <TextLink href="/privacy">{t.privacyPage}</TextLink>
    </>
  );
}

/**
 * One line of a section: what it is on the left, with a short explanation
 * under it, and the value or control on the right. Stacked on a phone.
 * A single control sits level with its name; a form of several fields is
 * read from the top, so its name stays at the top beside the first field.
 */
function Row({
  label,
  hint,
  labelFor,
  align = "center",
  children,
}: {
  label: string;
  hint?: string;
  labelFor?: string;
  align?: "center" | "top";
  children: ReactNode;
}) {
  const Name = labelFor ? "label" : "span";
  return (
    <div className={`grid gap-3 border-b border-line py-5 sm:grid-cols-[minmax(0,15rem)_minmax(0,1fr)] sm:gap-8 ${align === "top" ? "sm:items-start" : "sm:items-center"}`}>
      <div className="min-w-0">
        {label ? <Name {...(labelFor ? { htmlFor: labelFor } : {})} className="block text-sm font-semibold text-ink">{label}</Name> : null}
        {hint ? <p className="mt-1 text-[13px] leading-5 text-ink-muted">{hint}</p> : null}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Rows under their own heading, set apart from the settings above them. */
function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="pt-8">
      <h3 className="border-b border-line pb-3 text-base font-semibold text-ink">{title}</h3>
      {children}
    </div>
  );
}

function Value({ children }: { children: ReactNode }) {
  return <p className="text-sm leading-6 text-ink">{children}</p>;
}

function Note({ children }: { children: ReactNode }) {
  return <p className="text-sm leading-6 text-ink-muted">{children}</p>;
}

function TextLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="mt-5 inline-flex min-h-11 items-center text-sm font-semibold text-brand underline decoration-brand/30 underline-offset-4 transition-colors hover:decoration-brand motion-reduce:transition-none"
    >
      {children}
    </Link>
  );
}

function FormStatus({
  status,
  errorId,
}: {
  status: { kind: "idle" | "saving" | "saved" | "error"; message?: string };
  errorId?: string;
}) {
  if (status.kind === "error") {
    return <p id={errorId} role="alert" className="text-sm font-medium text-[color:var(--color-danger-text)]">{status.message}</p>;
  }
  // Kept in the page at no height while empty, so the announcement is heard when it fills.
  return (
    <p role="status" aria-live="polite" className="text-sm font-medium text-ink-muted empty:h-0">
      {status.kind === "saved" ? status.message : ""}
    </p>
  );
}
