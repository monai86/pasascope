"use client";

import Link from "next/link";

import { PracticeDashboardView } from "@/features/dashboard/components/practice-dashboard-view";
import { ApiError } from "@/lib/api";
import { getDashboardSummary, type DashboardSummary } from "@/lib/workflow";
import { useRemoteResource } from "@/services/adapters/use-remote-resource";

type DashboardLoad = { kind: "summary"; summary: DashboardSummary } | { kind: "denied" };

// The summary is loaded in the browser: the session token lives there, so a
// server-side fetch could only ever reach the API unauthenticated.
async function loadDashboard(_identity: string, signal: AbortSignal): Promise<DashboardLoad> {
  try {
    return { kind: "summary", summary: await getDashboardSummary({ signal }) };
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return { kind: "denied" };
    }
    throw error;
  }
}

export function PracticeDashboardClient() {
  const resource = useRemoteResource("dashboard:summary", loadDashboard);

  if (resource.status === "success" && resource.data.kind === "summary") {
    return <PracticeDashboardView summary={resource.data.summary} />;
  }
  if (resource.status === "loading" || resource.status === "idle") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-4xl items-center px-4 py-10 sm:px-6">
        <p role="status" className="text-sm text-ink-muted">
          Loading practice summary…
        </p>
      </main>
    );
  }
  return <DashboardUnavailable denied={resource.status === "success"} />;
}

function DashboardUnavailable({ denied }: { denied: boolean }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-4xl items-center px-4 py-10 sm:px-6">
      <section
        className="w-full rounded-2xl border border-line bg-surface p-8 shadow-xs text-ink"
        role="alert"
      >
        <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--color-attention-border)] bg-[color:var(--color-attention-bg)] px-3 py-1 text-xs font-semibold text-[color:var(--color-warning-text)]">
          <span>{denied ? "Sign-in required · ต้องเข้าสู่ระบบ" : "Backend Offline · หรือเซิร์ฟเวอร์กำลังเริ่มต้น"}</span>
        </div>
        <p className="sr-only">Dashboard unavailable</p>
        <h1 className="mt-3 text-2xl sm:text-3xl font-bold text-ink">
          Practice summary could not be loaded
        </h1>
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          {denied
            ? "Your session is not authorized to view the practice summary. กรุณาเข้าสู่ระบบอีกครั้ง หรือติดต่อผู้ดูแลองค์กร"
            : "The backend summary endpoint did not respond. เซิร์ฟเวอร์ API หลังบ้านอาจยังไม่ได้รัน ท่านสามารถทดลองใช้งานเคสสาธิต (Demo Cases) หรือสตูดิโอวิเคราะห์ได้ทันที"}
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            href="/today"
            className="inline-flex min-h-11 items-center rounded-xl bg-brand px-5 text-sm font-semibold text-white transition hover:bg-brand-hover"
          >
            Back to Today
          </Link>
          <Link
            href="/cases"
            className="inline-flex min-h-11 items-center rounded-xl border border-line bg-white px-5 text-sm font-semibold text-ink transition hover:bg-surface-muted"
          >
            ดูรายการเคสทั้งหมด (Cases)
          </Link>
          <Link
            href="/sessions/session_demo_001?view=findings"
            className="inline-flex min-h-11 items-center rounded-xl border border-brand-border bg-brand-soft px-5 text-sm font-semibold text-brand transition hover:bg-brand hover:text-white"
          >
            เปิดสตูดิโอวิเคราะห์ (Assessment Studio)
          </Link>
        </div>
      </section>
    </main>
  );
}
