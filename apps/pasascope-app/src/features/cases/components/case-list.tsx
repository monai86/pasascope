"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowRight, FolderPlus, Plus, Search, SearchX } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { CreateCaseForm } from "@/features/cases/components/create-case-form";
import type { CaseListViewModel } from "@/features/cases/hooks/use-cases-workspace";
import { statusMessages } from "@/components/status.messages";
import { casesMessages, type CaseNextAction, type CaseStage } from "@/features/cases/cases.messages";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import type { BackendCase } from "@/lib/workflow";

type Shared = (typeof casesMessages.en)["shared"];

const FOCUS = "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";
// One height and one edge for every control in the toolbar, so it reads as a single band.
const CONTROL = `min-h-11 rounded-control border border-line bg-surface text-sm text-ink outline-none transition motion-reduce:transition-none ${FOCUS}`;

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

function clinicianList(caseItem: BackendCase, shared: Shared) {
  const assigned = caseItem.care_team_user_ids ?? [];
  return assigned.length ? assigned.map(clinicianLabel).join(", ") : shared.noClinicianAssigned;
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
  const { locale } = useLocale();
  const [query, setQuery] = useState(initialQuery);
  const [statusFilter, setStatusFilter] = useState("all");
  const [consentFilter, setConsentFilter] = useState("all");
  const [clinicianFilter, setClinicianFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"latest-activity" | "next-action">("latest-activity");
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

  /** Code, age and language on one quiet line under the case's name. */
  function metaLine(caseItem: BackendCase) {
    return [
      codeLabel(caseItem),
      ageLabel(caseItem, shared),
      languageLabel(caseItem, shared),
      ...(caseItem.review_priority?.toLowerCase() === "high" ? [t.highPriority] : []),
    ].join(" · ");
  }

  function activityLabel(caseItem: BackendCase) {
    return caseItem.latest_session_date ? formatDate(caseItem.latest_session_date, locale) || caseItem.latest_session_date : t.noActivity;
  }

  // The page is one column: a heading, one band of controls, then the cases.
  // Each case appears once, with everything needed to act on it in its own row.
  return (
    <div className="space-y-5">
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

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-full sm:w-auto sm:min-w-[16rem] sm:flex-1">
            <label htmlFor="case-search" className="sr-only">
              {t.searchLabel}
            </label>
            <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-subtle" size={18} aria-hidden="true" />
            <input
              id="case-search"
              type="search"
              role="searchbox"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t.searchPlaceholder}
              className={`${CONTROL} w-full pl-11 pr-4 text-base placeholder:text-ink-subtle`}
            />
          </div>

          {canFilterByClinician && clinicianOptions.length ? (
            <select
              id="clinician-filter"
              aria-label={t.clinicianFilter}
              value={clinicianFilter}
              onChange={(event) => setClinicianFilter(event.target.value)}
              className={`${CONTROL} max-w-full px-3.5`}
            >
              <option value="all">{t.allClinicians}</option>
              {clinicianOptions.map((userId) => (
                <option key={userId} value={userId}>
                  {clinicianLabel(userId)}
                </option>
              ))}
            </select>
          ) : null}

          <select
            aria-label={t.consentFilter}
            value={consentFilter}
            onChange={(event) => setConsentFilter(event.target.value)}
            className={`${CONTROL} min-w-0 max-w-full flex-1 px-3.5 sm:flex-none`}
          >
            <option value="all">{t.allConsent}</option>
            <option value="granted">{t.consentActive}</option>
            <option value="pending">{t.consentPending}</option>
            <option value="withdrawn">{t.consentWithdrawn}</option>
          </select>

          {/* The options alone do not say they are an order, so this one keeps a visible word. */}
          <label className={`${CONTROL} inline-flex min-w-0 flex-1 items-center gap-2 pl-3.5 text-ink-muted focus-within:ring-4 focus-within:ring-[color:var(--color-focus-ring)] sm:flex-none`}>
            <span aria-hidden="true">{t.sortShort}</span>
            <select
              aria-label={t.sort}
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value as "latest-activity" | "next-action")}
              className="min-h-11 min-w-0 flex-1 rounded-control bg-transparent pr-2 font-medium text-ink outline-none"
            >
              <option value="latest-activity">{t.sortLatest}</option>
              <option value="next-action">{t.sortNext}</option>
            </select>
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          {/* With one status there is nothing to choose between. */}
          {stageOptions.length > 2 ? (
            <div className="flex flex-wrap gap-2" role="group" aria-label={t.statusFilters}>
              {stageOptions.map((option) => {
                const active = statusFilter === option;
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setStatusFilter(option)}
                    className={`inline-flex min-h-11 items-center rounded-full border px-4 text-sm transition motion-reduce:transition-none ${FOCUS} ${
                      active
                        ? "border-transparent bg-action font-semibold text-white"
                        : "border-line bg-surface font-medium text-ink-muted hover:text-ink"
                    }`}
                    aria-pressed={active}
                  >
                    {option === "all" ? t.allStatuses : statusLabels[option] ?? option}
                  </button>
                );
              })}
            </div>
          ) : (
            <span />
          )}
          <p className="text-sm text-ink-muted">{t.showing(filteredCases.length, cases.length)}</p>
        </div>
      </div>

      {filteredCases.length ? (
        <>
          <div className="hidden xl:block">
            <DataTable
              caption={t.tableCaption}
              columns={[
                { key: "case", header: t.columns.case },
                { key: "workflowStatus", header: t.columns.workflowStatus },
                { key: "latestActivity", header: t.columns.latestActivity },
                { key: "nextAction", header: t.columns.nextAction, align: "right" },
              ]}
              rows={filteredCases.map((caseItem) => {
                const action = nextAction(caseItem);
                return {
                  id: caseItem.case_id,
                  case: (
                    <div>
                      <Link
                        href={`/cases/${caseItem.case_id}`}
                        className={`inline-block rounded-control py-[11px] text-base font-semibold leading-snug text-ink underline-offset-4 hover:underline ${FOCUS}`}
                      >
                        {caseLabel(caseItem)}
                      </Link>
                      <p className="-mt-2 text-[13px] text-ink-muted">{metaLine(caseItem)}</p>
                    </div>
                  ),
                  workflowStatus: (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-ink">{shared.stages[workflowStage(caseItem)]}</span>
                      <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />
                    </div>
                  ),
                  latestActivity: <span className="whitespace-nowrap text-ink-muted">{activityLabel(caseItem)}</span>,
                  nextAction: (
                    <ActionButton href={action.href} tone="secondary" className="whitespace-nowrap">
                      <span className="inline-flex items-center gap-2">
                        {t.actions[action.key]}
                        <ArrowRight size={16} aria-hidden="true" />
                      </span>
                    </ActionButton>
                  ),
                };
              })}
            />
          </div>

          <ul className="reading-surface divide-y divide-line overflow-hidden xl:hidden" aria-label={t.listLabel}>
            {filteredCases.map((caseItem) => {
              const action = nextAction(caseItem);
              return (
                <li key={caseItem.case_id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-x-3">
                      <Link
                        href={`/cases/${caseItem.case_id}`}
                        className={`inline-block rounded-control py-[11px] text-base font-semibold leading-snug text-ink underline-offset-4 hover:underline ${FOCUS}`}
                      >
                        {caseLabel(caseItem)}
                      </Link>
                      <StatusBadge status={caseItem.latest_session_status ?? "Draft"} />
                    </div>
                    <p className="-mt-2 text-[13px] text-ink-muted">{metaLine(caseItem)}</p>
                    <p className="mt-1 text-sm text-ink-muted">
                      {shared.stages[workflowStage(caseItem)]} · {activityLabel(caseItem)}
                    </p>
                  </div>
                  <ActionButton href={action.href} tone="secondary" className="w-full shrink-0 whitespace-nowrap sm:w-auto">
                    <span className="inline-flex items-center gap-2">
                      {t.actions[action.key]}
                      <ArrowRight size={16} aria-hidden="true" />
                    </span>
                  </ActionButton>
                </li>
              );
            })}
          </ul>
        </>
      ) : cases.length === 0 ? (
        <EmptyState
          icon={FolderPlus}
          title={t.emptyTitle}
          description={canCreateCase ? t.emptyCanCreate : t.emptyCannotCreate}
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
      )}
    </div>
  );
}
