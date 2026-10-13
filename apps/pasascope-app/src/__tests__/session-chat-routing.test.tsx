import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionWorkspace } from "@/features/sessions/components/session-workspace";
import { resolveSessionHref, resolveSessionRouteView } from "@/features/sessions/state/session-view";

const settings = vi.hoisted(() => ({ reviewGates: "open" }));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock", access_model: { public_signup: true, review_gates: settings.reviewGates } },
  }),
}));

vi.mock("@/features/sessions/components/session-workspace-model", () => ({
  SessionChatWorkspace: () => <div>conversation</div>,
  SessionWorkflowWorkspace: ({ view }: { view: string }) => <div>workbench {view}</div>,
}));

afterEach(() => {
  vi.unstubAllEnvs();
  settings.reviewGates = "open";
});

describe("session route in the chat shell", () => {
  it("accepts chat as a view and still falls back to intake for anything unknown", () => {
    expect(resolveSessionRouteView("chat")).toBe("chat");
    expect(resolveSessionRouteView("transcript")).toBe("transcript");
    expect(resolveSessionRouteView("nonsense")).toBe("intake");
    expect(resolveSessionRouteView(undefined)).toBe("intake");
    expect(resolveSessionHref("chat", "s1", { caseId: "c1" })).toBe("/sessions/s1?view=chat&case_id=c1");
  });

  it("opens the conversation, which also answers links that still point at Intake", () => {
    const { rerender } = render(<SessionWorkspace sessionId="s1" view="chat" />);
    expect(screen.getByText("conversation")).toBeInTheDocument();

    rerender(<SessionWorkspace sessionId="s1" view="intake" />);
    expect(screen.getByText("conversation")).toBeInTheDocument();
  });

  it("keeps the transcript and findings as full pages in the chat shell", () => {
    const { rerender } = render(<SessionWorkspace sessionId="s1" view="transcript" />);
    expect(screen.getByText("workbench transcript")).toBeInTheDocument();

    rerender(<SessionWorkspace sessionId="s1" view="findings" />);
    expect(screen.getByText("workbench findings")).toBeInTheDocument();
  });
});
