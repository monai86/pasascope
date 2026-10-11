import { AppShell } from "@/components/app-shell";
import { PracticeDashboardClient } from "@/features/dashboard/components/practice-dashboard-client";

export default function DashboardPage() {
  return (
    <AppShell active="Dashboard">
      <PracticeDashboardClient />
    </AppShell>
  );
}
