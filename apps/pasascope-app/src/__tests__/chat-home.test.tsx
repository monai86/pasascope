import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatHome } from "@/features/chat-home/chat-home";
import type { BackendCase } from "@/lib/workflow";

const api = vi.hoisted(() => ({
  cases: [] as BackendCase[],
  getDashboardSummary: vi.fn(),
  listBackendCases: vi.fn(),
  createBackendCase: vi.fn(),
}));

vi.mock("@/lib/workflow", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/workflow")>()),
  getDashboardSummary: api.getDashboardSummary,
  listBackendCases: api.listBackendCases,
  createBackendCase: api.createBackendCase,
}));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock", access_model: { public_signup: true, review_gates: "open" } },
  }),
}));

function session(overrides: Record<string, unknown>) {
  return {
    session_id: "s1",
    case_id: "case-a",
    case_label: "Tonkla",
    session_date: "2026-10-12",
    status: "Needs Review",
    has_transcript: true,
    has_features: false,
    has_ml_review: false,
    has_report: false,
    ...overrides,
  };
}

beforeEach(() => {
  api.cases = [{ case_id: "case-a", child_code: "PS-0142", nickname: "Tonkla", consent_status: "granted" }];
  api.getDashboardSummary.mockReset().mockResolvedValue({ recent_sessions: [session({})] });
  api.listBackendCases.mockReset().mockImplementation(async () => [...api.cases]);
  api.createBackendCase.mockReset().mockImplementation(async (payload: Partial<BackendCase>) => {
    const created = { case_id: "case-new", consent_status: "pending", ...payload } as BackendCase;
    api.cases = [...api.cases, created];
    return created;
  });
});

describe("chat home", () => {
  it("greets, offers three ways to begin and points at the session left open", async () => {
    render(<ChatHome />);

    expect(screen.getByRole("heading", { name: "What would you like to do today?" })).toBeInTheDocument();
    expect(screen.getByTestId("home-card-record")).toHaveTextContent("Record new audio");
    expect(screen.getByTestId("home-card-upload")).toHaveTextContent("Upload an audio file");

    // The card becomes a link once there is a session to open.
    await waitFor(() => expect(screen.getByTestId("home-card-resume")).toHaveTextContent("Tonkla · Transcript to check"));
    expect(screen.getByTestId("home-card-resume")).toHaveAttribute("href", "/sessions/s1?view=chat&case_id=case-a");
  });

  it("has nothing to pick up when no session is waiting", async () => {
    api.getDashboardSummary.mockResolvedValue({ recent_sessions: [] });
    render(<ChatHome />);

    await waitFor(() => expect(screen.getByTestId("home-card-resume")).toHaveTextContent("Nothing waiting"));
    expect(screen.getByTestId("home-card-resume")).not.toHaveAttribute("href");
  });

  it("finds a case from what is typed in the composer", async () => {
    render(<ChatHome />);
    await waitFor(() => expect(api.listBackendCases).toHaveBeenCalled());

    fireEvent.change(screen.getByRole("textbox", { name: "Find a case" }), { target: { value: "tonk" } });
    fireEvent.click(screen.getByRole("button", { name: "Find case" }));

    const pick = await screen.findByTestId("start-pick-case");
    expect(within(pick).getByRole("button", { name: /Tonkla/ })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Find a case" })).toBeEnabled();
    expect(screen.queryByRole("heading", { name: "What would you like to do today?" })).toBeNull();
  });

  it("keeps the conversation going after a new case is created, and asks for consent next", async () => {
    render(<ChatHome />);
    await waitFor(() => expect(api.listBackendCases).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId("home-card-record"));
    fireEvent.click(await screen.findByTestId("start-new-case"));
    const form = screen.getByTestId("start-new-case-form");
    fireEvent.change(within(form).getByLabelText("Case code"), { target: { value: "PS-0200" } });
    fireEvent.change(within(form).getByLabelText("Age: years"), { target: { value: "4" } });
    fireEvent.change(within(form).getByLabelText("Age: months"), { target: { value: "2" } });
    fireEvent.click(within(form).getByRole("button", { name: "Create case" }));

    // The case list is read again in the background; the chosen case must survive that.
    expect(await screen.findByTestId("start-consent")).toBeInTheDocument();
    // Typing only finds a case, so the field is inert once one is chosen.
    expect(screen.getByRole("textbox", { name: "Find a case" })).toBeDisabled();
    await waitFor(() => expect(api.listBackendCases).toHaveBeenCalledTimes(2));
    expect(screen.getByTestId("start-consent")).toBeInTheDocument();
    expect(screen.queryByTestId("start-pick-case")).toBeNull();
    expect(api.createBackendCase).toHaveBeenCalledWith(
      expect.objectContaining({ child_code: "PS-0200", age_months: 50, consent_status: "pending" }),
    );
  });

  it("says so when the workspace cannot be read, instead of showing an empty one", async () => {
    api.getDashboardSummary.mockRejectedValue(new Error("offline"));
    render(<ChatHome />);

    fireEvent.click(screen.getByTestId("home-card-record"));
    expect(await screen.findByText("Sessions could not be loaded.")).toBeInTheDocument();
    expect(screen.queryByTestId("start-pick-case")).toBeNull();
  });
});
