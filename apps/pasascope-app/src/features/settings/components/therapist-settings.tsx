"use client";

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Bell,
  Building2,
  Download,
  Eye,
  HelpCircle,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import type { SharedSettingsSection } from "@/features/settings/services/settings-access";
import { settingsMessages } from "@/features/settings/settings.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useConfirmedRuntimeSettings } from "@/lib/confirmed-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useSafetyCopy } from "@/lib/safety-copy";

const SECTION_ICONS: Record<SharedSettingsSection, LucideIcon> = {
  account: UserRound,
  organization: Building2,
  accessibility: Eye,
  notifications: Bell,
  privacy: LockKeyhole,
  export: Download,
  help: HelpCircle,
};

type LineTone = "default" | "muted" | "warning";

// Tone of each line, by position, where it is not the default.
const LINE_TONES: Partial<Record<SharedSettingsSection, Record<number, LineTone>>> = {
  organization: { 3: "muted" },
  accessibility: { 1: "muted" },
  notifications: { 1: "muted", 2: "muted", 3: "warning" },
  privacy: { 2: "muted" },
  export: { 2: "muted" },
};

export function TherapistSettings({ section }: { section: SharedSettingsSection }) {
  const t = useMessages(settingsMessages);
  const safety = useSafetyCopy();
  const card = t.cards[section];
  const runtimeSettings = useConfirmedRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  // With real sign-in, show who is signed in rather than the demo values.
  const signedIn = runtimeSettings?.auth_mode === "supabase";
  const signedInValues: Partial<Record<SharedSettingsSection, Record<number, string>>> = signedIn
    ? {
        account: {
          0: supabaseSession?.displayName ?? supabaseSession?.email ?? t.signedIn.fallbackName,
          1: supabaseSession?.role ?? card.lines[1][1],
          3: t.signedIn.dataMode,
        },
        organization: { 1: t.signedIn.dataMode },
        privacy: { 0: t.signedIn.authentication },
      }
    : {};
  const settingsCard = (
    <SettingsCard icon={SECTION_ICONS[section]} title={t.sections[section]} description={card.description}>
      {card.lines.map(([label, value], index) => (
        <SettingLine
          key={label}
          label={label}
          // The clinical boundary line shows the registered safety label.
          value={signedInValues[section]?.[index] ?? (value || safety.DECISION_SUPPORT_ONLY_LABEL)}
          tone={LINE_TONES[section]?.[index]}
        />
      ))}
    </SettingsCard>
  );

  if (section !== "privacy") return settingsCard;

  return (
    <div className="grid gap-4">
      {settingsCard}
      <section className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-5 text-[color:var(--color-warning-text)]" aria-labelledby="owned-privacy-requests-title">
        <div className="flex items-start gap-3">
          <ShieldCheck size={22} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <h2 id="owned-privacy-requests-title" className="text-lg font-semibold">{t.privacyRequests.title}</h2>
            <p className="mt-2 text-sm font-semibold">{t.privacyRequests.unavailable}</p>
            <p className="mt-1 text-sm leading-6">{t.privacyRequests.body}</p>
            <p className="mt-2 text-sm leading-6">{t.privacyRequests.noClaim}</p>
          </div>
        </div>
      </section>
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
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand border border-[color:var(--color-brand-border)]/60">
          <Icon size={21} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-xl font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-ink-muted">{description}</p>
        </div>
      </div>
      <div className="mt-5 divide-y divide-line/70 rounded-control border border-line bg-field">
        {children}
      </div>
    </section>
  );
}

function SettingLine({ label, tone = "default", value }: { label: string; tone?: LineTone; value: string }) {
  const valueClassName = tone === "warning" ? "text-[color:var(--color-warning-text)]" : tone === "muted" ? "text-ink-muted" : "text-ink";
  return (
    <div className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[180px_1fr]">
      <span className="font-medium text-ink-muted">{label}</span>
      <span className={`font-semibold ${valueClassName}`}>{value}</span>
    </div>
  );
}
