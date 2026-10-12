"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { dashboardMessages } from "@/features/dashboard/dashboard.messages";
import type { Locale } from "@/i18n/config";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import type {
  DashboardTrendCase,
  DashboardTrendFeature,
  DashboardTrendPoint,
  DashboardTrendReference,
} from "@/lib/workflow";

const CHART_WIDTH = 640;
const CHART_HEIGHT = 176;
const PAD_X = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 14;

type Trends = {
  features: DashboardTrendFeature[];
  cases: DashboardTrendCase[];
};

type TrendPointWithValue = DashboardTrendPoint & { value: number };

function formatDate(value: string, locale: Locale): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(locale === "th" ? "th-TH" : undefined, { month: "short", day: "numeric" });
}

function formatValue(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return String(parseFloat(value.toFixed(2)));
}

function pointsForFeature(
  trendCase: DashboardTrendCase | undefined,
  featureKey: string,
): TrendPointWithValue[] {
  if (!trendCase) return [];
  return trendCase.points
    .map((point) => ({
      ...point,
      value: typeof point.values[featureKey] === "number" ? (point.values[featureKey] as number) : Number.NaN,
    }))
    .filter((point) => Number.isFinite(point.value));
}

function ChartGeometry({
  points,
  reference,
  caseId,
}: {
  points: TrendPointWithValue[];
  reference?: { q1: number; median: number; q3: number } | null;
  caseId: string;
}) {
  const t = useMessages(dashboardMessages).chart;
  const { locale } = useLocale();
  const values = points.map((point) => point.value);
  const rawMin = Math.min(...values, ...(reference ? [reference.q1, reference.q3] : []));
  const rawMax = Math.max(...values, ...(reference ? [reference.q1, reference.q3] : []));
  const range = rawMax - rawMin || 1;
  const min = rawMin - range * 0.18;
  const max = rawMax + range * 0.18;
  const innerWidth = CHART_WIDTH - PAD_X * 2;
  const innerHeight = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;

  const x = (index: number) =>
    points.length === 1
      ? CHART_WIDTH / 2
      : PAD_X + (index * innerWidth) / (points.length - 1);
  const y = (value: number) =>
    PAD_TOP + innerHeight - ((value - min) / (max - min)) * innerHeight;

  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${x(index).toFixed(1)},${y(point.value).toFixed(1)}`)
    .join(" ");

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        role="img"
        aria-label={t.lineChart(points.length)}
        className="h-auto w-full text-brand-strong"
        preserveAspectRatio="xMidYMid meet"
      >
        {reference ? (
          <>
            <rect
              x={PAD_X}
              y={y(reference.q3)}
              width={CHART_WIDTH - PAD_X * 2}
              height={Math.max(y(reference.q1) - y(reference.q3), 1)}
              fill="currentColor"
              opacity={0.08}
            />
            <line
              x1={PAD_X}
              y1={y(reference.median)}
              x2={CHART_WIDTH - PAD_X}
              y2={y(reference.median)}
              stroke="currentColor"
              strokeOpacity={0.4}
              strokeWidth={1}
              strokeDasharray="4 4"
            />
          </>
        ) : null}
        <line
          x1={PAD_X}
          y1={CHART_HEIGHT - PAD_BOTTOM}
          x2={CHART_WIDTH - PAD_X}
          y2={CHART_HEIGHT - PAD_BOTTOM}
          stroke="currentColor"
          strokeOpacity={0.15}
          strokeWidth={1}
        />
        {points.length > 1 ? (
          <path
            d={linePath}
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : null}
        {points.map((point, index) => (
          <circle
            key={`${point.session_id}-dot`}
            cx={x(index)}
            cy={y(point.value)}
            r={5}
            fill="currentColor"
          />
        ))}
      </svg>
      {points.map((point, index) => (
        <a
          key={point.session_id}
          href={`/sessions/${encodeURIComponent(point.session_id)}?case_id=${encodeURIComponent(caseId)}`}
          aria-label={t.openSession(formatDate(point.session_date, locale))}
          className="absolute z-10 grid min-h-11 min-w-11 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full opacity-0 transition focus-visible:opacity-100 focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
          style={{
            left: `${(x(index) / CHART_WIDTH) * 100}%`,
            top: `${(y(point.value) / CHART_HEIGHT) * 100}%`,
          }}
        />
      ))}
    </div>
  );
}

export function LanguageProgressChart({ trends }: { trends?: Trends }) {
  const t = useMessages(dashboardMessages).chart;
  const { locale } = useLocale();
  const safeTrends: Trends = {
    features: trends?.features ?? [],
    cases: trends?.cases ?? [],
  };
  // The backend can return many cases that share a label (e.g. repeated test
  // children). Dedupe by label, keeping the entry with the most points, so the
  // picker stays usable instead of listing hundreds of near-identical options.
  const uniqueCases = useMemo(() => {
    const byLabel = new Map<string, DashboardTrendCase>();
    for (const trendCase of safeTrends.cases) {
      const existing = byLabel.get(trendCase.case_label);
      if (!existing || trendCase.points.length > existing.points.length) {
        byLabel.set(trendCase.case_label, trendCase);
      }
    }
    return [...byLabel.values()].sort((a, b) => b.points.length - a.points.length);
  }, [safeTrends.cases]);
  const [featureKey, setFeatureKey] = useState(safeTrends.features[0]?.key ?? "");
  const [caseId, setCaseId] = useState(uniqueCases[0]?.case_id ?? "");

  const feature = safeTrends.features.find((item) => item.key === featureKey) ?? safeTrends.features[0];
  const selectedCase = uniqueCases.find((item) => item.case_id === caseId) ?? uniqueCases[0];

  const points = pointsForFeature(selectedCase, feature?.key ?? "");
  const reference = selectedCase?.reference?.features[feature?.key ?? ""] ?? null;
  const referenceMeta = selectedCase?.reference;

  if (!feature || uniqueCases.length === 0) {
    return (
      <p className="mt-4 rounded-card border border-dashed border-line p-5 text-sm leading-6 text-ink-muted">
        {t.empty}
      </p>
    );
  }

  const singleCase = uniqueCases.length === 1 ? selectedCase : undefined;
  const sessionHref = (sessionId: string) =>
    `/sessions/${encodeURIComponent(sessionId)}?case_id=${encodeURIComponent(selectedCase.case_id)}`;

  return (
    <div className="mt-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="grid min-w-0 gap-1 text-sm font-medium text-ink-muted">
          {t.feature}
          <select
            className="min-h-11 w-full min-w-0 max-w-full rounded-card border border-line bg-surface px-3 text-sm text-ink outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] sm:w-56"
            value={feature.key}
            onChange={(event) => setFeatureKey(event.target.value)}
          >
            {safeTrends.features.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        {uniqueCases.length > 1 ? (
          <label className="grid min-w-0 gap-1 text-sm font-medium text-ink-muted">
            {t.case}
            <select
              className="min-h-11 w-full min-w-0 max-w-full rounded-card border border-line bg-surface px-3 text-sm text-ink outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] sm:w-56"
              value={selectedCase.case_id}
              onChange={(event) => setCaseId(event.target.value)}
            >
              {uniqueCases.map((item) => (
                <option key={item.case_id} value={item.case_id}>
                  {item.case_label}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <p className="text-sm font-medium text-ink-muted">
            {t.caseValue} <span className="text-ink">{singleCase?.case_label}</span>
          </p>
        )}
      </div>

      {points.length === 0 ? (
        <p className="mt-5 rounded-card border border-dashed border-line p-5 text-sm leading-6 text-ink-muted">
          {t.noData(feature.label, selectedCase.case_label)}
        </p>
      ) : (
        <>
          {points.length === 1 ? (
            <p className="mt-4 text-sm leading-6 text-ink-muted">
              {t.oneSession(feature.label)}
            </p>
          ) : null}
          <div className="mt-4">
            <ChartGeometry points={points} reference={reference} caseId={selectedCase.case_id} />
            <p className="mt-1 text-xs text-ink-subtle">
              {t.unit(feature.unit, points.length)}
            </p>
            {reference && referenceMeta ? (
              <p className="mt-1 text-xs text-ink-subtle">
                {t.reference(String(referenceMeta.age_band), String(referenceMeta.task_type), formatValue(reference.median), formatValue(reference.q1), formatValue(reference.q3))}
              </p>
            ) : null}
          </div>
          <table className="mt-4 w-full max-w-sm border-collapse text-sm">
            <caption className="sr-only">
              {t.tableCaption(feature.label, selectedCase.case_label)}
            </caption>
            <thead>
              <tr className="border-b border-line text-left">
                <th scope="col" className="py-2 pr-4 font-medium text-ink-muted">
                  {t.sessionDate}
                </th>
                <th scope="col" className="py-2 font-medium text-ink-muted">
                  {feature.label}
                </th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.session_id} className="border-b border-line last:border-b-0">
                  <td className="py-1 pr-4">
                    <Link
                      href={sessionHref(point.session_id)}
                      className="inline-flex min-h-11 items-center rounded-lg px-1 font-medium text-brand-strong transition hover:bg-brand-soft"
                    >
                      {formatDate(point.session_date, locale)}
                    </Link>
                  </td>
                  <td className="py-2 font-semibold text-ink">{formatValue(point.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
