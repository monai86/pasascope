"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, Filter, FolderPlus, Plus, Search, SearchX } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { CreateCaseForm } from "@/features/cases/components/create-case-form";
import type { CaseListViewModel } from "@/features/cases/hooks/use-cases-workspace";
import { statusMessages } from "@/components/status.messages";
import { casesMessages, type CaseNextAction, type CaseStage } from "@/features/cases/cases.messages";
import { useMessages } from "@/i18n/locale-provider";
import type { BackendCase } from "@/lib/workflow";

type Shared = (typeof casesMessages.en)["shared"];

function ageLabel(caseItem: BackendCase, shared: Shared) {
  if (caseItem.age_months == null) return shared.ageNotRecorded;
  return shared.age(Math.floor(caseItem.age_months / 12), caseItem.age_months % 12);
}

function caseLabel(caseItem: BackendCase) {
  return caseItem.nickname ?? caseItem.child_code ?? caseItem.display_label ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function codeLabel(caseItem: BackendCase) {
  return caseItem.child_code ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function languageLabel(caseItem: BackendCase, shared: Shared) {
  return caseItem.language ?? shared.languageNotRecorded;
}

function clinicianLabel(userId: string) {
  if (userId === "therapist-demo") return "Demo Therapist";
  return userId
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function primaryClinician(caseItem: BackendCase, shared: Shared) {
  if (caseItem.primary_therapist_user_id) return clinicianLabel(caseItem.primary_therapist_user_id);
  const assigned = caseItem.care_team_user_ids ?? [];
  return assigned.length ? clinicianLabel(assigned[0]) : shared.notAssigned;
}

function clinicianList(caseItem: BackendCase, shared: Shared) {
  const assigned = caseItem.care_team_user_ids ?? [];
  return assigned.length ? assigned.map(clinicianLabel).join(", ") : shared.noClinicianAssigned;
}

function childInitials(caseItem: BackendCase) {
  const label = caseLabel(caseItem);
  const words = label.split(/\s+/).filter(Boolean);
  return words.slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "").join("") || codeLabel(caseItem).slice(-2);
}

function consentLabel(value: string | undefined, shared: Shared) {
  if (!value) return shared.consentUnknown;
  return shared.consentStates[value.toLowerCase()] ?? value;
}

function workflowStage(caseItem: BackendCase): CaseStage {
  if (caseItem.consent_status && caseItem.consent_status !== "granted") return "consent";
  if (caseItem.latest_session_status === "Needs Review") return "transcript";
  if (caseItem.latest_report_status === "Ready") return "signOff";
  if (caseItem.latest_session_status === "Attested") return "drafting";
  if (caseItem.latest_session_date) return "session";
  return "intake";
}

function nextAction(caseItem: BackendCase): { key: CaseNextAction; href: string } {
  if (caseItem.consent_status && caseItem.consent_status !== "granted") {
    return { key: "reviewConsent", href: `/cases/${caseItem.case_id}` };
  }
  if (caseItem.latest_session_status === "Needs Review") {
    return { key: "reviewSession", href: `/cases/${caseItem.case_id}` };
  }
  if (caseItem.latest_report_status === "Ready") {
    return { key: "finalizeReport", href: `/cases/${caseItem.case_id}` };
  }
  if (caseItem.latest_session_date) {
    return { key: "continueWorkflow", href: `/cases/${caseItem.case_id}` };
  }
  return { key: "startSession", href: `/cases?intent=start-session&case_id=${encodeURIComponent(caseItem.case_id)}` };
}

export function CaseList({
  model,
  canFilterByClinician = false,
  canCreateCase = false,
  initialQuery = "",
}: {
  model: CaseListViewModel;
  canFilterByClinician?: boolean;
  canCreateCase?: boolean;
  initialQuery?: string;
}) {
  const { cases } = model;
  const { shared, list: t } = useMessages(casesMessages);
  const statusLabels = useMessages(statusMessages) as Record<string, string>;
  const [query, setQuery] = useState(initialQuery);
  const [statusFilter, setStatusFilter] = useState("all");
  const [consentFilter, setConsentFilter] = useState("all");
  const [clinicianFilter, setClinicianFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"latest-activity" | "next-action">("latest-activity");
  const [selectedCaseId, setSelectedCaseId] = useState(cases[0]?.case_id ?? "");
  const [showCreateForm, setShowCreateForm] = useState(false);

  function clearFilters() {
    setQuery("");
    setStatusFilter("all");
    setConsentFilter("all");
    setClinicianFilter("all");
  }

  const stageOptions = useMemo(() => {
    const statuses = Array.from(new Set(cases.map((item) => item.latest_session_status ?? "Draft")));
    return ["all", ...statuses];
  }, [cases]);

  const clinicianOptions = useMemo(() => {
    return Array.from(new Set(cases.flatMap((item) => item.care_team_user_ids ?? [])));
  }, [cases]);

  const filteredCases = useMemo(() => {
    const filtered = cases.filter((caseItem) => {
      const matchesSearch = !query || [
        caseLabel(caseItem),
        codeLabel(caseItem),
        languageLabel(caseItem, shared),
        clinicianList(caseItem, shared)
      ].join(" ").toLowerCase().includes(query.toLowerCase());
      const matchesStatus = statusFilter === "all" || (caseItem.latest_session_status ?? "Draft") === statusFilter;
      const matchesConsent = consentFilter === "all" || (caseItem.consent_status ?? "unknown").toLowerCase() === consentFilter;
      const matchesClinician = clinicianFilter === "all" || (caseItem.care_team_user_ids ?? []).includes(clinicianFilter);
      return matchesSearch && matchesStatus && matchesConsent && matchesClinician;
    });
    return filtered.sort((left, right) => {
      if (sortBy === "next-action") {
        return shared.stages[workflowStage(left)].localeCompare(shared.stages[workflowStage(right)]) || caseLabel(left).localeCompare(caseLabel(right));
      }
      return (right.latest_session_date ?? "").localeCompare(left.latest_session_date ?? "")
        || caseLabel(left).localeCompare(caseLabel(right));
    });
  }, [cases, clinicianFilter, consentFilter, query, shared, sortBy, statusFilter]);

  const selectedCase = filteredCases.find((caseItem) => caseItem.case_id === selectedCaseId) ?? filteredCases[0];

  return (
    <>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-6">
          <PageHeader
            title={t.title}
            description={t.description}
            actions={
              <>
                <ActionButton href="/assessments" tone="secondary">
                  {t.startAssessment}
                </ActionButton>
                {canCreateCase ? (
                  <ActionButton
                    type="button"
                    icon={<Plus size={18} aria-hidden="true" />}
                    onClick={() => setShowCreateForm((visible) => !visible)}
                  >
                    {showCreateForm ? t.closeForm : t.createCase}
                  </ActionButton>
                ) : null}
              </>
            }
          />

          {showCreateForm ? <CreateCaseForm onCancel={() => setShowCreateForm(false)} /> : null}

          <section className="rounded-2xl border border-line bg-surface p-5 sm:p-6 shadow-2xs">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="flex-1">
                <label htmlFor="case-search" className="mb-2 block text-xs font-bold uppercase tracking-wider text-ink">
                  {t.searchLabel}
                </label>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-subtle" size={17} aria-hidden="true" />
                  <input
                    id="case-search"
                    type="search"
                    role="searchbox"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={t.searchPlaceholder}
                    className="min-h-11 w-full rounded-xl border border-line bg-white pl-10 pr-4 text-sm text-ink outline-none transition focus:border-brand focus:ring-2 focus:ring-[color:var(--color-brand)]/20"
                  />
                </div>
              </div>

              {canFilterByClinician && clinicianOptions.length ? (
                <div className="w-full lg:max-w-[16rem]">
                  <label htmlFor="clinician-filter" className="mb-2 block text-xs font-bold uppercase tracking-wider text-ink">
                    {t.clinicianFilter}
                  </label>
                  <select
                    id="clinician-filter"
                    aria-label={t.clinicianFilter}
                    value={clinicianFilter}
                    onChange={(event) => setClinicianFilter(event.target.value)}
                    className="min-h-11 w-full rounded-xl border border-line bg-white px-3.5 text-sm text-ink outline-none transition focus:border-brand focus:ring-2 focus:ring-[color:var(--color-brand)]/20"
                  >
                    <option value="all">{t.allClinicians}</option>
                    {clinicianOptions.map((userId) => (
                      <option key={userId} value={userId}>
                        {clinicianLabel(userId)}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label={t.statusFilters}>
              {stageOptions.map((option) => {
                const active = statusFilter === option;
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setStatusFilter(option)}
                    className={`inline-flex min-h-10 items-center gap-2 rounded-xl border px-3.5 py-1.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                      active
                        ? "border-brand bg-brand-soft text-brand font-bold shadow-2xs"
                        : "border-line bg-white text-ink-muted hover:bg-surface-muted"
                    }`}
                    aria-pressed={active}
                  >
                    <Filter size={14} aria-hidden="true" />
                    {option === "all" ? t.allStatuses : statusLabels[option] ?? option}
                  </button>
                );
              })}
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 pt-3 border-t border-[color:var(--color-border)]/60">
              <label className="grid gap-1.5 text-xs font-bold uppercase tracking-wider text-ink">
                {t.consentFilter}
                <select
                  aria-label={t.consentFilter}
                  value={consentFilter}
                  onChange={(event) => setConsentFilter(event.target.value)}
                  className="min-h-10 min-w-0 rounded-xl border border-line bg-white px-3 text-xs font-medium text-ink outline-none transition focus:border-brand sm:px-3.5"
                >
                  <option value="all">{t.allConsent}</option>
                  <option value="granted">{t.consentActive}</option>
                  <option value="pending">{t.consentPending}</option>
                  <option value="withdrawn">{t.consentWithdrawn}</option>
                </select>
              </label>
              <label className="grid gap-1.5 text-xs font-bold uppercase tracking-wider text-ink">
                {t.sort}
                <select
                  aria-label={t.sort}
                  value={sortBy}
                  onChange={(event) => setSortBy(event.target.value as "latest-activity" | "next-action")}
                  className="min-h-10 min-w-0 rounded-xl border border-line bg-white px-3 text-xs font-medium text-ink outline-none transition focus:border-brand sm:px-3.5"
                >
                  <option value="latest-activity">{t.sortLatest}</option>
                  <option value="next-action">{t.sortNext}</option>
                </select>
              </label>
            </div>
          </section>

          {filteredCases.length ? (
            <>
              <div className="hidden xl:block">
                <DataTable
                  caption={t.tableCaption}
                  columns={[
                    { key: "case", header: t.columns.case },
                    { key: "latestActivity", header: t.columns.latestActivity },
                    { key: "workflowStatus", header: t.columns.workflowStatus },
                    { key: "nextAction", header: t.columns.nextAction }
                  ]}
                  selectedId={selectedCase?.case_id}
                  onSelect={setSelectedCaseId}
                  rows={filteredCases.map((caseItem) => {
                    const action = nextAction(caseItem);
                    return {
                      id: caseItem.case_id,
                      case: (
                        <div className="space-y-1">
                          <Link href={`/cases/${caseItem.case_id}`} className="inline-flex min-h-11 items-center font-semibold text-ink hover:text-brand-strong">
                            {caseLabel(caseItem)}
                          </Link>
                          <p className="text-xs text-ink-muted">
                            {codeLabel(caseItem)}
                          </p>
                        </div>
                      ),
                      latestActivity: (
                        <p className="text-sm text-ink-muted">
                          {caseItem.latest_session_date ?? t.noActivity}
                        </p>
                      ),
                      workflowStatus: (
                        <div className="space-y-1">
                          <p className="font-medium text-ink">{shared.stages[workflowStage(caseItem)]}</p>
                          <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />
                        </div>
                      ),
                      nextAction: (
                        <Link
                          href={action.href}
                          className="inline-flex min-h-11 items-center gap-2 rounded-card border border-line px-4 py-2 font-medium text-ink transition hover:border-brand-strong hover:bg-brand-soft"
                        >
                          {t.actions[action.key]}
                          <ArrowRight size={16} aria-hidden="true" />
                        </Link>
                      )
                    };
                  })}
                />
              </div>

              <ul className="xl:hidden space-y-3" aria-label={t.listLabel}>
                {filteredCases.map((caseItem) => {
                  const action = nextAction(caseItem);
                  const selected = selectedCase?.case_id === caseItem.case_id;
                  return (
                    <li
                      key={caseItem.case_id}
                      className={`rounded-2xl border transition-all ${
                        selected
                          ? "border-brand-border bg-brand-soft shadow-2xs"
                          : "border-line bg-surface shadow-2xs"
                      }`}
                    >
                      <div className="p-4 space-y-3">
                        <div className="flex items-start gap-3">
                          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-xs font-bold text-brand border border-[color:var(--color-brand-border)]/60">
                            {childInitials(caseItem)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <Link
                                href={`/cases/${caseItem.case_id}`}
                                className="inline-flex min-h-10 items-center font-bold text-ink hover:text-brand"
                              >
                                {caseLabel(caseItem)}
                              </Link>
                              <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />
                            </div>
                            <p className="text-xs text-ink-muted">
                              {shared.stages[workflowStage(caseItem)]} · {caseItem.latest_session_date ?? t.noActivity}
                            </p>
                          </div>
                        </div>
                        <div className="pt-2 border-t border-[color:var(--color-border)]/50">
                          <Link
                            href={action.href}
                            className="inline-flex min-h-10 w-full items-center justify-center gap-1.5 rounded-xl border border-line bg-white px-4 text-xs font-bold text-brand transition hover:border-brand-border hover:bg-brand-soft shadow-2xs"
                          >
                            <span>{t.actions[action.key]}</span>
                            <ArrowRight size={14} aria-hidden="true" />
                          </Link>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            cases.length === 0 ? (
              <EmptyState
                icon={FolderPlus}
                title={t.emptyTitle}
                description={canCreateCase
                  ? t.emptyCanCreate
                  : t.emptyCannotCreate}
                action={canCreateCase && !showCreateForm ? (
                  <ActionButton icon={Plus} onClick={() => setShowCreateForm(true)}>{t.createFirst}</ActionButton>
                ) : undefined}
              />
            ) : (
              // Cases exist but the search and filters hide them all: say so,
              // and offer the way back rather than "no cases".
              <EmptyState
                icon={SearchX}
                title={t.noMatchTitle}
                description={t.noMatchBody}
                action={<ActionButton tone="secondary" onClick={clearFilters}>{t.clearFilters}</ActionButton>}
              />
            )
          )}

          <footer className="control-strip rounded-xl border border-line bg-white px-4 py-3 text-xs font-medium text-ink-muted shadow-2xs">
            {t.showing(filteredCases.length, cases.length)}
          </footer>

        </div>

        <aside className="space-y-4" aria-label={t.selectedContext}>
          <section className="rounded-2xl border border-line bg-surface p-6 shadow-2xs hidden lg:block">
            <p className="text-xs font-bold uppercase tracking-wider text-ink-subtle pb-3 border-b border-[color:var(--color-border)]/60">{t.selectedContext}</p>
            {selectedCase ? (
              <div className="mt-4 space-y-4">
                <div>
                  <h2 className="text-lg font-bold text-ink">{caseLabel(selectedCase)}</h2>
                  <p className="mt-1 text-xs text-ink-muted">
                    {codeLabel(selectedCase)} · {ageLabel(selectedCase, shared)} · {languageLabel(selectedCase, shared)}
                  </p>
                </div>
                <div className="rounded-xl border border-brand-border bg-brand-soft p-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-brand">{t.columns.nextAction}</p>
                  <p className="mt-1 font-bold text-ink text-sm">{t.actions[nextAction(selectedCase).key]}</p>
                  <ActionButton href={nextAction(selectedCase).href} className="mt-3 w-full" tone="primary">
                    {t.actions[nextAction(selectedCase).key]}
                  </ActionButton>
                </div>
                <dl className="grid gap-2 text-xs">
                  <div className="flex items-center justify-between gap-3 border-b border-[color:var(--color-border)]/60 py-2">
                    <dt className="text-ink-muted">{t.columns.workflowStatus}</dt>
                    <dd className="font-semibold text-ink">{shared.stages[workflowStage(selectedCase)]}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-3 border-b border-[color:var(--color-border)]/60 py-2">
                    <dt className="text-ink-muted">{t.columns.latestActivity}</dt>
                    <dd className="font-semibold text-ink">{selectedCase.latest_session_date ?? t.noneYet}</dd>
                  </div>
                </dl>
                <details className="responsive-details rounded-xl border border-line bg-[color:var(--color-surface-muted)]/40">
                  <summary className="flex min-h-10 cursor-pointer items-center justify-between px-3 text-xs font-bold text-ink">
                    <span>{t.moreContext}</span>
                    <span aria-hidden="true">›</span>
                  </summary>
                  <dl className="space-y-2 border-t border-line p-3 text-xs text-ink-muted">
                    <div><dt className="font-bold text-ink">{t.consentAndPriority}</dt><dd>{t.consentWithPriority(consentLabel(selectedCase.consent_status, shared), selectedCase.review_priority ? t.priority(selectedCase.review_priority) : t.priorityNotSet)}</dd></div>
                    <div><dt className="font-bold text-ink">{t.latestReport}</dt><dd>{t.reportStatus(selectedCase.latest_report_status ? statusLabels[selectedCase.latest_report_status] ?? selectedCase.latest_report_status : shared.notStarted.toLowerCase())}</dd></div>
                    <div><dt className="font-bold text-ink">{t.primaryClinician}</dt><dd>{primaryClinician(selectedCase, shared)}</dd></div>
                  </dl>
                </details>
                <ActionButton href={`/cases/${encodeURIComponent(selectedCase.case_id)}`} tone="secondary" className="w-full">
                  {t.openDetail}
                </ActionButton>
              </div>
            ) : (
              <p className="mt-3 text-xs leading-6 text-ink-muted">{t.noSelection}</p>
            )}
          </section>
        </aside>
      </div>
    </>
  );
}
