"use client";

import { useEffect, useState } from "react";
import { Building2, LockKeyhole, ShieldCheck } from "lucide-react";

import { loginMessages } from "@/components/login.messages";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useMessages } from "@/i18n/locale-provider";
import { type RuntimeSettings } from "@/lib/api";
import {
  MOCK_ORGANIZATION_OPTIONS,
  type MockRole,
  saveMockAccessSession,
} from "@/lib/mock-access-session";

// Today is the single home; organisation admins start in the admin settings.
const roleDestinations: Record<MockRole, string> = {
  therapist: "/today?role=therapist",
  clinical_supervisor: "/today?role=clinical_supervisor",
  org_admin: "/settings?scope=admin&role=org_admin"
};

export function MockLoginFormClient({
  runtimeSettings,
}: {
  runtimeSettings: RuntimeSettings | null;
}) {
  const t = useMessages(loginMessages).mock;
  const [role, setRole] = useState<MockRole>("therapist");
  const [organizationId, setOrganizationId] = useState(MOCK_ORGANIZATION_OPTIONS.therapist[0].organizationId);
  const [aal, setAal] = useState<"aal1" | "aal2">("aal2");
  const destination = roleDestinations[role];
  const organizationOptions = MOCK_ORGANIZATION_OPTIONS[role];
  const requiresExplicitOrganizationSelection = organizationOptions.length > 1;

  useEffect(() => {
    setOrganizationId(MOCK_ORGANIZATION_OPTIONS[role][0].organizationId);
  }, [role]);

  return (
    <form className="rounded-panel border border-line bg-surface p-6 shadow-lift sm:p-8" aria-label={t.formLabel}>
      <div className="mb-6 flex items-start gap-3">
        <span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-items-center rounded-control bg-brand-soft text-brand">
          <ShieldCheck size={20} />
        </span>
        <div>
          <h2 className="text-xl font-semibold text-ink">{t.title}</h2>
          <p className="mt-1 text-sm leading-6 text-ink-muted">{t.description}</p>
        </div>
      </div>

      <div className="grid gap-4">
        <Field label={t.email}>
          {(control) => <Input {...control} defaultValue="therapist@example.test" type="email" autoComplete="off" />}
        </Field>
        <Field label={t.role}>
          {(control) => (
            <Select {...control} value={role} onChange={(event) => setRole(event.target.value as MockRole)}>
              <option value="therapist">{t.roles.therapist}</option>
              <option value="clinical_supervisor">{t.roles.clinical_supervisor}</option>
              <option value="org_admin">{t.roles.org_admin}</option>
            </Select>
          )}
        </Field>
        <Field label={t.organization}>
          {(control) => (
            <Select {...control} value={organizationId} onChange={(event) => setOrganizationId(event.target.value)}>
              {organizationOptions.map((option) => (
                <option key={option.organizationId} value={option.organizationId}>
                  {option.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t.assurance}>
          {(control) => (
            <Select {...control} value={aal} onChange={(event) => setAal(event.target.value as "aal1" | "aal2")}>
              <option value="aal2">AAL2</option>
              <option value="aal1">AAL1</option>
            </Select>
          )}
        </Field>
      </div>

      <p className="mt-4 text-sm leading-6 text-ink-muted" aria-live="polite">{t.destination[role]}</p>

      <div className="mt-4 rounded-card border border-line bg-surface-muted p-4 text-sm leading-6 text-ink-muted">
        <div className="flex items-start gap-2">
          <Building2 size={16} aria-hidden="true" className="mt-1 shrink-0" />
          <div>
            <p className="font-semibold text-ink">{t.organizationNote.title}</p>
            <p className="mt-1">
              {requiresExplicitOrganizationSelection ? t.organizationNote.multiple : t.organizationNote.single}
            </p>
            <p className="mt-1">
              {t.organizationNote.aalBefore}<strong>AAL1</strong>{t.organizationNote.aalMiddle}<strong>AAL2</strong>{t.organizationNote.aalAfter}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-card border border-brand-border bg-brand-soft p-4 text-sm leading-6 text-brand-strong">
        <div className="flex items-start gap-2">
          <LockKeyhole size={16} aria-hidden="true" className="mt-1 shrink-0" />
          <div>
            <p className="font-semibold">{t.boundary.title}</p>
            <p className="mt-1">
              {runtimeSettings?.access_model?.invitation_only === false ? t.boundary.open : t.boundary.invitationOnly}
            </p>
            <p className="mt-1">{t.boundary.localOnly}</p>
          </div>
        </div>
      </div>

      <Button
        href={destination}
        onClick={() => saveMockAccessSession({ role, organizationId, aal })}
        size="lg"
        className="mt-6 w-full"
      >
        {t.submit}
      </Button>
    </form>
  );
}
