"use client";

import { useState } from "react";
import { ClipboardCheck, FileText, Inbox, LayoutGrid, Rows3 } from "lucide-react";

import { designSystemMessages } from "@/app/demo/design-system/design-system.messages";
import { LanguageToggle } from "@/components/language-toggle";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { StatusBadge } from "@/components/status-badge";
import {
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  Input,
  SegmentedControl,
  Select,
  StatTile,
  Stepper,
} from "@/components/ui";
import { useMessages } from "@/i18n/locale-provider";

const swatches = {
  sixty: ["--color-page-bg", "--color-surface-strong", "--color-surface", "--color-surface-muted", "--color-border"],
  thirty: ["--color-sky-soft", "--color-sky", "--color-sky-strong", "--color-text-muted", "--color-text-strong", "--color-navy"],
  ten: ["--color-brand", "--color-brand-hover", "--color-brand-soft", "--color-highlight", "--color-highlight-soft"],
} as const;

const statuses = ["Draft", "Processing", "Needs Review", "Attested", "Report Ready", "Signed Off", "Awaiting Consent", "Recording", "Failed"];

function Swatches({ title, tokens }: { title: string; tokens: readonly string[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <ul className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3" role="list">
        {tokens.map((token) => (
          <li key={token} className="overflow-hidden rounded-control border border-line bg-surface">
            <span aria-hidden="true" className="block h-14" style={{ background: `var(${token})` }} />
            <code className="block truncate px-2 py-1.5 text-xs text-ink-muted">{token.replace("--color-", "")}</code>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Section({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <section className="rounded-panel border border-line bg-surface p-5 shadow-soft sm:p-6">
      <h2 className="text-xl font-semibold text-ink">{heading}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default function DesignSystemPage() {
  const t = useMessages(designSystemMessages);
  const [view, setView] = useState<"table" | "cards">("table");
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <main className="mx-auto grid max-w-5xl gap-6 p-4 sm:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <PasaScopeLogo size="lg" />
          <h1 className="mt-5 text-3xl font-semibold text-ink">{t.title}</h1>
          <p className="mt-2 max-w-[65ch] text-sm leading-6 text-ink-muted">{t.intro}</p>
        </div>
        <LanguageToggle />
      </header>

      <Section heading={t.colour.heading}>
        <div className="grid gap-6">
          <Swatches title={t.colour.sixty} tokens={swatches.sixty} />
          <Swatches title={t.colour.thirty} tokens={swatches.thirty} />
          <Swatches title={t.colour.ten} tokens={swatches.ten} />
          <p className="text-sm leading-6 text-ink-muted">{t.colour.rule}</p>
        </div>
      </Section>

      <Section heading={t.type.heading}>
        <p className="text-xs font-semibold uppercase tracking-wider text-ink-subtle">{t.type.display}</p>
        <p className="mt-1 font-display text-3xl font-semibold text-ink">{t.type.sample}</p>
        <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-ink-subtle">{t.type.body}</p>
        <p className="mt-1 text-base leading-7 text-ink">{t.type.sample}</p>
      </Section>

      <Section heading={t.actions.heading}>
        <div className="flex flex-wrap gap-3">
          <Button>{t.actions.primary}</Button>
          <Button variant="secondary">{t.actions.secondary}</Button>
          <Button variant="ghost">{t.actions.ghost}</Button>
          <Button variant="danger">{t.actions.danger}</Button>
          <Button loading>{t.actions.loading}</Button>
          <Button disabled>{t.actions.disabled}</Button>
        </div>
      </Section>

      <Section heading={t.status.heading}>
        <div className="flex flex-wrap gap-2">
          {statuses.map((status) => (
            <StatusBadge key={status} status={status} />
          ))}
        </div>
        <p className="mt-4 text-sm leading-6 text-ink-muted">{t.status.note}</p>
      </Section>

      <Section heading={t.forms.heading}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t.forms.label} hint={t.forms.hint}>
            {(control) => <Input {...control} placeholder={t.forms.placeholder} />}
          </Field>
          <Field label={t.forms.label} error={t.forms.error} required>
            {(control) => <Input {...control} />}
          </Field>
          <Field label={t.forms.select}>
            {(control) => (
              <Select {...control} defaultValue="th">
                <option value="th">ไทย</option>
                <option value="en">English</option>
              </Select>
            )}
          </Field>
          <div className="grid content-start gap-1.5">
            <span className="text-sm font-semibold text-ink">{t.forms.view}</span>
            <SegmentedControl
              label={t.forms.view}
              value={view}
              onChange={setView}
              options={[
                { value: "table", label: t.forms.table, icon: Rows3 },
                { value: "cards", label: t.forms.cards, icon: LayoutGrid },
              ]}
            />
          </div>
        </div>
      </Section>

      <Section heading={t.surfaces.heading}>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="p-5">
            <h3 className="text-base font-semibold text-ink">{t.surfaces.plain}</h3>
            <p className="mt-1 text-sm leading-6 text-ink-muted">{t.surfaces.plainBody}</p>
          </Card>
          <div className="rounded-card bg-[image:linear-gradient(120deg,var(--color-sky-soft),var(--color-sky))] p-4">
            <Card variant="glass" className="p-5">
              <h3 className="text-base font-semibold text-ink">{t.surfaces.glass}</h3>
              <p className="mt-1 text-sm leading-6 text-ink-muted">{t.surfaces.glassBody}</p>
            </Card>
          </div>
          <Card variant="hero" className="p-6 md:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-wider">{t.surfaces.heroEyebrow}</p>
            <h3 className="mt-2 text-2xl font-semibold">{t.surfaces.heroTitle}</h3>
            <p className="mt-1 max-w-[60ch] text-sm leading-6">{t.surfaces.heroBody}</p>
            <Button className="mt-4 border-white bg-surface text-brand-strong hover:bg-brand-soft" variant="secondary">
              {t.surfaces.heroAction}
            </Button>
          </Card>
        </div>
      </Section>

      <Section heading={t.stats.heading}>
        <div className="grid gap-3 sm:grid-cols-3">
          <StatTile label={t.stats.needsAction} value={2} icon={Inbox} tone="attention" />
          <StatTile label={t.stats.ready} value={5} icon={FileText} tone="brand" />
          <StatTile label={t.stats.signed} value={12} icon={ClipboardCheck} />
        </div>
      </Section>

      <Section heading={t.steps.heading}>
        <Stepper
          label={t.steps.rail}
          stateLabels={{ complete: t.steps.complete, current: t.steps.current, available: t.steps.available, locked: t.steps.locked }}
          steps={[
            { id: "intake", label: t.steps.intake, state: "complete" },
            { id: "transcript", label: t.steps.transcript, state: "current" },
            { id: "findings", label: t.steps.findings, state: "locked" },
            { id: "report", label: t.steps.report, state: "locked" },
          ]}
        />
      </Section>

      <Section heading={t.states.heading}>
        <div className="grid gap-4 md:grid-cols-2">
          <EmptyState title={t.states.emptyTitle} description={t.states.emptyBody} action={<Button>{t.states.emptyAction}</Button>} />
          <ErrorState title={t.states.errorTitle} description={t.states.errorBody} retryLabel={t.states.retry} onRetry={() => {}} />
        </div>
      </Section>

      <Section heading={t.dialog.heading}>
        <Button variant="danger" onClick={() => setConfirmOpen(true)}>{t.dialog.open}</Button>
        <ConfirmDialog
          open={confirmOpen}
          title={t.dialog.title}
          description={t.dialog.body}
          confirmLabel={t.dialog.confirm}
          cancelLabel={t.dialog.cancel}
          destructive
          onConfirm={() => setConfirmOpen(false)}
          onCancel={() => setConfirmOpen(false)}
        />
      </Section>
    </main>
  );
}
