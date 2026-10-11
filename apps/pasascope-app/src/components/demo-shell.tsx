"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  FileText,
  LayoutGrid,
  Mic,
  BarChart3,
  ClipboardList,
  Users,
  UploadCloud,
} from "lucide-react";

import { PasaScopeLogoMark } from "@/components/pasascope-logo";

type DemoNavItem = {
  href: string;
  label: string;
  labelTh: string;
  icon: typeof LayoutGrid;
  step?: number;
};

const navItems: DemoNavItem[] = [
  { href: "/demo/dashboard", label: "Dashboard", labelTh: "หน้าแรก", icon: LayoutGrid },
  { href: "/demo/upload", label: "Upload", labelTh: "อัปโหลด", icon: UploadCloud, step: 1 },
  { href: "/demo/transcript", label: "Transcript", labelTh: "บทสนทนา", icon: FileText, step: 2 },
  { href: "/demo/features", label: "Features", labelTh: "วิเคราะห์", icon: BarChart3, step: 3 },
  { href: "/demo/report", label: "Report", labelTh: "รายงาน", icon: ClipboardList, step: 4 },
  { href: "/demo/parent", label: "Parent Portal", labelTh: "ผู้ปกครอง", icon: Users },
];

export function DemoShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <div className="mx-auto flex max-w-[1600px]">
        {/* Sidebar */}
        <aside className="sticky top-0 hidden h-dvh w-20 shrink-0 border-r border-line bg-surface-muted px-3 py-6 md:flex md:flex-col md:items-center lg:w-[17.5rem] lg:px-5 lg:items-stretch">
          <Link href="/demo/dashboard" className="flex items-center gap-3 rounded-panel px-2 py-2">
            <PasaScopeLogoMark size="sm" />
            <span className="hidden lg:block">
              <span className="block text-lg font-normal tracking-[-0.03em] text-ink">PasaScope</span>
              <span className="block text-sm text-ink-muted">Therapist Workspace</span>
            </span>
          </Link>

          <nav className="mt-8 w-full space-y-1.5" aria-label="Demo navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  title={item.label}
                  className={`flex min-h-11 items-center gap-3 rounded-full px-3 lg:px-4 text-sm font-medium justify-center lg:justify-start transition duration-200 ease-out motion-reduce:transition-none ${
                    isActive
                      ? "bg-brand text-white"
                      : "text-ink-muted hover:bg-white hover:text-ink"
                  }`}
                >
                  {item.step != null ? (
                    <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold ${
                      isActive ? "bg-white/20 text-white" : "bg-brand-soft text-brand-strong"
                    }`}>
                      {item.step}
                    </span>
                  ) : (
                    <Icon size={18} aria-hidden="true" className="shrink-0" />
                  )}
                  <span className="hidden lg:flex flex-col leading-tight">
                    <span>{item.label}</span>
                    <span className={`text-xs ${isActive ? "text-white/70" : "text-ink-subtle"}`}>{item.labelTh}</span>
                  </span>
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto hidden w-full space-y-3 lg:block">
            <div className="rounded-panel border border-line bg-surface p-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">Workflow</p>
              <div className="mt-3 flex items-center gap-1.5">
                {[1, 2, 3, 4].map((step) => {
                  const currentStep = navItems.find((n) => n.href === pathname)?.step ?? 0;
                  return (
                    <div
                      key={step}
                      className={`h-1.5 flex-1 rounded-full transition-colors ${
                        step <= currentStep ? "bg-brand" : "bg-line"
                      }`}
                    />
                  );
                })}
              </div>
              <p className="mt-2 text-xs text-ink-muted">
                Upload → Transcript → Features → Report
              </p>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Top bar */}
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-line bg-white px-6">
            <div className="flex items-center gap-3 md:hidden">
              <PasaScopeLogoMark size="xs" />
              <span className="text-sm font-semibold">PasaScope</span>
            </div>
            <div className="hidden md:block" />
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-sm font-semibold text-ink">Dr. Somchai K.</p>
                <p className="text-xs text-ink-muted">นักแก้ไขการพูด</p>
              </div>
              <div className="grid h-10 w-10 place-items-center rounded-full border border-line bg-brand-soft text-sm font-bold text-brand-strong">
                SK
              </div>
            </div>
          </header>

          {/* Mobile nav */}
          <nav className="flex items-center gap-1 overflow-x-auto border-b border-line bg-surface-muted px-4 py-2 md:hidden">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                    isActive
                      ? "bg-brand text-white"
                      : "text-ink-muted hover:bg-white"
                  }`}
                >
                  <Icon size={14} aria-hidden="true" />
                  {item.labelTh}
                </Link>
              );
            })}
          </nav>

          <main className="mx-auto w-full max-w-[1280px] flex-1 px-4 pb-6 pt-6 sm:px-6 sm:pb-8 lg:px-10 lg:pb-12 lg:pt-10">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
