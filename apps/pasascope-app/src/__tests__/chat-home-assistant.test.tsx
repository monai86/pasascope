import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { localIsoDate } from "@/features/chat-home/assistant/replies";
import { ChatHome } from "@/features/chat-home/chat-home";
import type { BackendCase } from "@/lib/workflow";

const api = vi.hoisted(() => ({
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
    session_date: "2026-10-01",
    status: "Needs Review",
    has_transcript: true,
    has_features: false,
    has_ml_review: false,
    has_report: false,
    ...overrides,
  };
}

const CASES: BackendCase[] = [{ case_id: "case-a", child_code: "PS-0142", nickname: "Tonkla", consent_status: "granted" }];

beforeEach(() => {
  api.getDashboardSummary.mockReset().mockResolvedValue({
    recent_sessions: [
      session({ session_id: "s-today", case_label: "Mali", session_date: localIsoDate() }),
      session({ session_id: "s-old", case_label: "Tonkla" }),
      session({ session_id: "s-done", case_label: "Fah", has_features: true, has_report: true }),
    ],
  });
  api.listBackendCases.mockReset().mockResolvedValue(CASES);
  api.createBackendCase.mockReset();
});

async function renderHome() {
  render(<ChatHome />);
  // The cases and sessions have arrived once the card names the session left open.
  await waitFor(() => expect(screen.getByTestId("home-card-resume")).toHaveTextContent("Mali"));
}

function type(line: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "Ask PasaScope or find a case" }), { target: { value: line } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

async function lastAnswer() {
  await waitFor(() => expect(screen.queryByText("PasaScope is answering…")).toBeNull(), { timeout: 3000 });
  const answers = await screen.findAllByTestId("home-answer");
  return answers[answers.length - 1];
}

describe("questions typed on the chat home", () => {
  it("answers what it can do, in place of the greeting, and says it is not an AI", async () => {
    await renderHome();
    type("What can you do?");

    expect(await screen.findByTestId("home-question")).toHaveTextContent("What can you do?");
    expect(screen.queryByRole("heading", { name: "What would you like to do today?" })).toBeNull();
    const answer = await lastAnswer();
    expect(answer).toHaveTextContent("Record the session, or upload an audio file");
    expect(answer).toHaveTextContent("It is not an AI that can talk about anything.");
    expect(screen.getByRole("textbox", { name: "Ask PasaScope or find a case" })).toHaveValue("");
  });

  it("shows that an answer is on its way before it arrives", async () => {
    await renderHome();
    type("how do I use it");

    expect(await screen.findByText("PasaScope is answering…")).toBeInTheDocument();
    const answer = await lastAnswer();
    expect(within(answer).getAllByRole("listitem")).toHaveLength(5);
    expect(answer).toHaveTextContent("Confirm the caregiver's consent");
  });

  it("lists the sessions dated today from the caller's own records", async () => {
    await renderHome();
    type("วันนี้มีเคสอะไรบ้าง");

    const answer = await lastAnswer();
    expect(answer).toHaveTextContent("There is 1 session dated today.");
    expect(answer).toHaveTextContent("1 earlier session is still unfinished.");
    expect(within(answer).getByRole("link", { name: /Mali/ })).toHaveAttribute("href", "/sessions/s-today?view=chat&case_id=case-a");
    expect(within(answer).queryByRole("link", { name: /Tonkla/ })).toBeNull();
  });

  it("lists unfinished sessions and the caller's cases", async () => {
    await renderHome();
    type("anything unfinished?");
    const pending = await lastAnswer();
    expect(pending).toHaveTextContent("2 sessions are unfinished.");
    expect(within(pending).queryByRole("link", { name: /Fah/ })).toBeNull();

    type("show my cases");
    await waitFor(() => expect(screen.getAllByTestId("home-question")).toHaveLength(2));
    const cases = await lastAnswer();
    expect(cases).toHaveTextContent("You have 1 case.");
    expect(within(cases).getByRole("link", { name: /Tonkla/ })).toHaveAttribute("href", "/cases/case-a");
  });

  it("says so when it does not understand, and offers questions it can answer", async () => {
    await renderHome();
    type("tell me a joke");

    const answer = await lastAnswer();
    expect(answer).toHaveTextContent("PasaScope did not understand that.");
    fireEvent.click(within(answer).getByRole("button", { name: "How do I use it?" }));

    await waitFor(() => expect(screen.getAllByTestId("home-question")).toHaveLength(2));
    expect(screen.getAllByTestId("home-question")[1]).toHaveTextContent("How do I use it?");
    expect(await lastAnswer()).toHaveTextContent("One session takes five steps:");
  });

  it("offers to look for a case when the line could be a name", async () => {
    await renderHome();
    type("Nong Mai");

    const answer = await lastAnswer();
    fireEvent.click(within(answer).getByRole("button", { name: "Look for “Nong Mai” in cases" }));

    expect(await screen.findByText("No case matches “Nong Mai”.")).toBeInTheDocument();
  });

  it("still finds a case by its name", async () => {
    await renderHome();
    type("tonk");

    const pick = await screen.findByTestId("start-pick-case");
    expect(within(pick).getByRole("button", { name: /Tonkla/ })).toBeInTheDocument();
    expect(screen.queryByTestId("home-answer")).toBeNull();
  });

  it("begins the guided start for a typed request to record, without creating anything", async () => {
    await renderHome();
    type("อยากอัดเสียงใหม่");

    // The typed line is the first bubble and the case is still to be chosen with a button.
    expect(await screen.findByTestId("start-pick-case")).toBeInTheDocument();
    expect(screen.getByText("อยากอัดเสียงใหม่")).toBeInTheDocument();
    expect(api.createBackendCase).not.toHaveBeenCalled();
  });

  it("explains that nothing is deleted from the field", async () => {
    await renderHome();
    type("ลบเคสทั้งหมด");

    const answer = await lastAnswer();
    expect(answer).toHaveTextContent("Nothing can be deleted from this field");
    expect(within(answer).getByRole("link", { name: "Open Cases" })).toHaveAttribute("href", "/cases");
  });

  it("reads a line typed on the wrong keyboard layout and says how it read it", async () => {
    await renderHome();
    type("mewiwfh[hk'");

    const answer = await lastAnswer();
    expect(answer).toHaveTextContent("Read as “ทำไรได้บ้าง”");
    expect(answer).toHaveTextContent("It is not an AI that can talk about anything.");
  });

  it("asks a suggested question from the greeting, and goes back to the start", async () => {
    await renderHome();
    fireEvent.click(screen.getByTestId("home-suggest-howto"));

    const answer = await lastAnswer();
    expect(answer).toHaveTextContent("One session takes five steps:");
    fireEvent.click(within(answer).getByRole("button", { name: "Back to the start" }));

    expect(screen.getByRole("heading", { name: "What would you like to do today?" })).toBeInTheDocument();
    expect(screen.queryByTestId("home-answer")).toBeNull();
  });
});
