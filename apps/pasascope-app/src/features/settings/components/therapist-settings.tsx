"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { HelpCircle, LockKeyhole, MonitorSmartphone, UserRound, Workflow } from "lucide-react";

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

const SECTION_ICONS: Record<SettingsSection, LucideIcon> = {
  account: UserRound,
  display: MonitorSmartphone,
  workflow: Workflow,
  privacy: LockKeyhole,
  help: HelpCircle,
};

export function TherapistSettings({ section }: { section: SettingsSection }) {
  const t = useMessages(settingsMessages);
  return (
    <SettingsCard icon={SECTION_ICONS[section]} title={t.sections[section]} description={t.descriptions[section]}>
      {section === "account" ? <AccountSettings /> : null}
      {section === "display" ? <DisplaySettings /> : null}
      {section === "workflow" ? <WorkflowSettings /> : null}
      {section === "privacy" ? <PrivacySettings /> : null}
      {section === "help" ? <HelpSettings /> : null}
    </SettingsCard>
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
    const client = getSupabaseBrowserClient();
    if (!client) return setStatus({ kind: "error", message: t.failed });
    setStatus({ kind: "saving" });
    const { error } = await client.auth.updateUser({ data: { display_name: trimmed } });
    setStatus(error ? { kind: "error", message: t.failed } : { kind: "saved", message: t.saved });
  }

  return (
    <div className="grid gap-5">
      <InfoLines
        lines={[
          ...(signedIn ? [[t.email, session?.email ?? t.fallbackName] as const] : []),
          [t.workspace, t.workspaceValue],
        ]}
      />
      {signedIn ? (
        <form onSubmit={saveName} className="grid gap-3" noValidate>
          <Field label={t.name} hint={t.nameHint} error={status.kind === "error" ? status.message : undefined}>
            {(control) => (
              <Input
                {...control}
                value={name}
                maxLength={80}
                autoComplete="name"
                onChange={(event) => {
                  setName(event.target.value);
                  if (status.kind !== "saving") setStatus({ kind: "idle" });
                }}
              />
            )}
          </Field>
          <FormActions status={status.kind === "saved" ? status.message : undefined}>
            <Button type="submit" loading={status.kind === "saving"} disabled={status.kind === "saving" || name.trim() === currentName}>
              {status.kind === "saving" ? t.saving : t.save}
            </Button>
          </FormActions>
        </form>
      ) : (
        <Note>{t.localOnly}</Note>
      )}
    </div>
  );
}

function DisplaySettings() {
  const t = useMessages(settingsMessages);
  const copy = t.display;
  const { locale, change } = useLanguageSwitch();
  const [preferences, update] = usePreferences();

  return (
    <div className="grid gap-5">
      <Choice label={copy.language}>
        <SegmentedControl<Locale>
          label={copy.language}
          value={locale}
          onChange={change}
          options={[
            { value: "th", label: "ไทย" },
            { value: "en", label: "English" },
          ]}
        />
      </Choice>
      <Choice label={copy.textSize} hint={t.savedHere}>
        <SegmentedControl<"standard" | "large">
          label={copy.textSize}
          value={preferences.textSize}
          onChange={(value) => update("textSize", value)}
          options={[
            { value: "standard", label: copy.standard },
            { value: "large", label: copy.large },
          ]}
        />
      </Choice>
      <Choice label={copy.motion} hint={`${copy.motionHint} ${t.savedHere}`}>
        <SegmentedControl<"system" | "reduce">
          label={copy.motion}
          value={preferences.motion}
          onChange={(value) => update("motion", value)}
          options={[
            { value: "system", label: copy.followDevice },
            { value: "reduce", label: copy.reduce },
          ]}
        />
      </Choice>
    </div>
  );
}

function WorkflowSettings() {
  const t = useMessages(settingsMessages);
  const copy = t.workflow;
  const [preferences, update] = usePreferences();
  const { externalTranscription } = useAppMode();

  return (
    <div className="grid gap-5">
      <Choice label={copy.caseLanguage} hint={`${copy.caseLanguageHint} ${t.savedHere}`}>
        <SegmentedControl<"Thai" | "English">
          label={copy.caseLanguage}
          value={preferences.caseLanguage}
          onChange={(value) => update("caseLanguage", value)}
          options={[
            { value: "Thai", label: copy.thai },
            { value: "English", label: copy.english },
          ]}
        />
      </Choice>
      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-ink">{copy.facts}</h3>
        <InfoLines
          lines={[
            [copy.transcription, externalTranscription ? copy.transcriptionExternal : copy.transcriptionLocal],
            [copy.review, copy.reviewValue],
            [copy.sharing, copy.sharingValue],
          ]}
        />
      </div>
    </div>
  );
}

function PrivacySettings() {
  const t = useMessages(settingsMessages).privacy;
  const signedIn = useSignedInAccounts();

  return (
    <div className="grid gap-6">
      {signedIn ? (
        <>
          <ChangePassword />
          <SignOutEverywhere />
        </>
      ) : (
        <Note>{t.localOnly}</Note>
      )}
      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-ink">{t.dataTitle}</h3>
        <InfoLines lines={t.dataLines} />
        <Link href="/privacy" className="justify-self-start text-sm font-semibold text-brand underline-offset-4 hover:underline">
          {t.privacyPage}
        </Link>
      </div>
    </div>
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
    <form onSubmit={submit} className="grid gap-3" noValidate aria-labelledby="change-password-title">
      <h3 id="change-password-title" className="text-sm font-semibold text-ink">{t.passwordTitle}</h3>
      <div className="grid gap-3 sm:grid-cols-2 sm:items-start">
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
      </div>
      {status.kind === "error" && !status.field ? <p role="alert" className="text-sm font-medium text-[color:var(--color-danger-text)]">{status.message}</p> : null}
      <FormActions status={status.kind === "saved" ? status.message : undefined}>
        <Button type="submit" loading={status.kind === "saving"} disabled={status.kind === "saving" || !password}>
          {status.kind === "saving" ? t.changing : t.change}
        </Button>
      </FormActions>
    </form>
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
    <div className="grid gap-2 border-t border-line pt-5">
      <h3 className="text-sm font-semibold text-ink">{t.everywhereTitle}</h3>
      <p className="text-sm leading-6 text-ink-muted">{t.everywhereBody}</p>
      {failed ? <p role="alert" className="text-sm font-medium text-[color:var(--color-danger-text)]">{t.everywhereFailed}</p> : null}
      <div>
        <Button variant="secondary" onClick={signOutEverywhere} loading={busy} disabled={busy}>
          {busy ? t.everywhereBusy : t.everywhereButton}
        </Button>
      </div>
    </div>
  );
}

function HelpSettings() {
  const t = useMessages(settingsMessages).help;
  const safety = useSafetyCopy();
  return (
    <div className="grid gap-3">
      {/* The clinical boundary line shows the registered safety label. */}
      <InfoLines lines={t.lines.map(([label, value]) => [label, value || safety.DECISION_SUPPORT_ONLY_LABEL] as const)} />
      <Link href="/privacy" className="justify-self-start text-sm font-semibold text-brand underline-offset-4 hover:underline">
        {t.privacyPage}
      </Link>
    </div>
  );
}

function SettingsCard({
  children,
  description,
  icon: Icon,
  title,
}: {
  children: ReactNode;
  description: string;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <section className="rounded-card border border-line bg-surface p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-[color:var(--color-brand-border)]/60 bg-brand-soft text-brand">
          <Icon size={21} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-xl font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-ink-muted">{description}</p>
        </div>
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

/** One setting: its name on the left (above on a phone), the control beside it. */
function Choice({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="grid gap-2 sm:grid-cols-[180px_1fr] sm:items-start">
      {/* As tall as the control beside it, so the two read as one line. */}
      <span className="text-sm font-medium text-ink sm:flex sm:min-h-[3.25rem] sm:items-center">{label}</span>
      <div className="grid gap-1.5 justify-items-start">
        {children}
        {hint ? <p className="text-xs leading-5 text-ink-subtle">{hint}</p> : null}
      </div>
    </div>
  );
}

function InfoLines({ lines }: { lines: ReadonlyArray<readonly [string, string]> }) {
  return (
    <div className="divide-y divide-line/70 rounded-control border border-line bg-field">
      {lines.map(([label, value]) => (
        <div key={label} className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[180px_1fr]">
          <span className="font-medium text-ink-muted">{label}</span>
          <span className="font-semibold text-ink">{value}</span>
        </div>
      ))}
    </div>
  );
}

function FormActions({ children, status }: { children: ReactNode; status?: string }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {children}
      <p role="status" aria-live="polite" className="text-sm font-medium text-ink-muted">{status ?? ""}</p>
    </div>
  );
}

function Note({ children }: { children: ReactNode }) {
  return <p className="rounded-control border border-line bg-field px-4 py-3 text-sm leading-6 text-ink-muted">{children}</p>;
}
