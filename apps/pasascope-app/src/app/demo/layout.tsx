import { notFound } from "next/navigation";

import { DemoShell } from "@/components/demo-shell";
import { isDemoEnabled } from "@/services/adapters/demo-mode";

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  if (!isDemoEnabled()) {
    notFound();
  }

  return (
    <div className="min-h-dvh bg-canvas">
      <div
        role="status"
        className="sticky top-0 z-50 border-b border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-4 py-2 text-center text-sm font-semibold text-[color:var(--color-warning-text)]"
      >
        Sample data demonstration — no clinical record or workflow action is real.
      </div>
      <DemoShell>{children}</DemoShell>
    </div>
  );
}
