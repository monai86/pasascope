"use client";

import dynamic from "next/dynamic";

import { AppShell } from "@/components/app-shell";
import type { ShellActive } from "@/components/sidebar";
import { TodayContextRail } from "@/features/work-queue/components/today-context-rail";
import { TodayWorkbenchView } from "@/features/work-queue/components/today-workbench-view";
import { useTodayWorkbench } from "@/features/work-queue/hooks/use-today-workbench";
import { useChatShellEnabled } from "@/lib/ui-shell";

// Loaded only in the chat shell, so the workbench route does not carry it.
const ChatHome = dynamic(() => import("@/features/chat-home/chat-home").then((module) => module.ChatHome));

export function WorkQueueDashboard({ active }: { active: ShellActive }) {
  return (
    <AppShell active={active}>
      <HomeWorkspace />
    </AppShell>
  );
}

/** The home screen of whichever shell is running: the chat home or the Today queue. */
function HomeWorkspace() {
  return useChatShellEnabled() ? <ChatHome /> : <TodayWorkspaceController />;
}

function TodayWorkspaceController() {
  const state = useTodayWorkbench();
  return (
    <div className="flex min-w-0 items-start gap-6">
      <div className="min-w-0 flex-1">
        <TodayWorkbenchView
          state={state}
          compactContext={<TodayContextRail state={state} titleId="today-context-compact" />}
        />
      </div>
      <aside className="hidden w-[var(--rail-width)] shrink-0 xl:block">
        <TodayContextRail state={state} titleId="today-context-rail" />
      </aside>
    </div>
  );
}
