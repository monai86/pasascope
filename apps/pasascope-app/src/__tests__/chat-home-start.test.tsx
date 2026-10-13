import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { routerPush } from "@/__tests__/setup";
import { StartSessionThread, type StartOpener } from "@/features/chat-home/start-session-thread";
import { takePendingSessionAudio } from "@/features/sessions/chat/pending-audio";
import type { BackendCase } from "@/lib/workflow";

const api = vi.hoisted(() => ({
  createBackendSessionForCase: vi.fn(),
  grantBackendCaseConsent: vi.fn(),
  calls: [] as string[],
}));

vi.mock("@/lib/workflow", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/workflow")>()),
  createBackendSessionForCase: api.createBackendSessionForCase,
  grantBackendCaseConsent: api.grantBackendCaseConsent,
}));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock", access_model: { public_signup: true, review_gates: "open" } },
  }),
}));

const consented: BackendCase = { case_id: "case-a", child_code: "PS-0142", nickname: "Tonkla", consent_status: "granted" };
const pending: BackendCase = { case_id: "case-b", child_code: "PS-0147", consent_status: "pending" };

function renderThread(opener: StartOpener, filter = "", cases: BackendCase[] = [consented, pending]) {
  return render(
    <StartSessionThread opener={opener} cases={cases} filter={filter} onCaseCreated={vi.fn()} onStartOver={vi.fn()} />,
  );
}

beforeEach(() => {
  api.calls = [];
  api.createBackendSessionForCase.mockReset().mockImplementation(async (caseId: string) => {
    api.calls.push(`create:${caseId}`);
    return { session_id: "session-1", case_id: caseId };
  });
  api.grantBackendCaseConsent.mockReset().mockImplementation(async (caseId: string) => {
    api.calls.push(`consent:${caseId}`);
    return { case_id: caseId, consent_status: "granted" };
  });
});

describe("starting a session from the chat home", () => {
  it("opens the session's conversation once a consented case is chosen", async () => {
    renderThread({ kind: "recording" });

    fireEvent.click(screen.getByRole("button", { name: /Tonkla/ }));

    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/sessions/session-1?view=chat&case_id=case-a&mode=recording"));
    // The session starts with empty notes, so they hold only what the therapist writes.
    expect(api.createBackendSessionForCase).toHaveBeenCalledWith("case-a", "recording", "");
    expect(api.grantBackendCaseConsent).not.toHaveBeenCalled();
  });

  it("asks for caregiver consent before any session exists for a case without it", async () => {
    renderThread({ kind: "audio" });

    fireEvent.click(screen.getByRole("button", { name: /PS-0147/ }));

    const consent = await screen.findByTestId("start-consent");
    expect(api.createBackendSessionForCase).not.toHaveBeenCalled();
    const confirm = within(consent).getByRole("button", { name: "Confirm and continue" });
    expect(confirm).toBeDisabled();

    fireEvent.click(within(consent).getByRole("checkbox"));
    fireEvent.click(within(consent).getByRole("button", { name: "Confirm and continue" }));

    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/sessions/session-1?view=chat&case_id=case-b&mode=audio"));
    expect(api.calls).toEqual(["consent:case-b", "create:case-b"]);
  });

  it("opens no session when consent could not be saved", async () => {
    api.grantBackendCaseConsent.mockRejectedValueOnce(new Error("offline"));
    renderThread({ kind: "recording" });

    fireEvent.click(screen.getByRole("button", { name: /PS-0147/ }));
    const consent = await screen.findByTestId("start-consent");
    fireEvent.click(within(consent).getByRole("checkbox"));
    fireEvent.click(within(consent).getByRole("button", { name: "Confirm and continue" }));

    expect(await screen.findByText("Consent could not be saved. Try again.")).toBeInTheDocument();
    expect(api.createBackendSessionForCase).not.toHaveBeenCalled();
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("asks what to do when the case was found by typing", async () => {
    renderThread({ kind: "search", text: "tonk" });

    expect(screen.queryByRole("button", { name: /PS-0147/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Tonkla/ }));

    const intent = await screen.findByTestId("start-pick-intent");
    expect(api.createBackendSessionForCase).not.toHaveBeenCalled();
    fireEvent.click(within(intent).getByRole("button", { name: "Upload an audio file" }));

    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/sessions/session-1?view=chat&case_id=case-a&mode=audio"));
  });

  it("offers to create a case when nothing matches what was typed", () => {
    renderThread({ kind: "findCase" }, "Mali");

    expect(screen.getByText("No case matches “Mali”.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create a new case called “Mali”" }));

    const form = screen.getByTestId("start-new-case-form");
    expect(within(form).getByLabelText(/Nickname/)).toHaveValue("Mali");
    fireEvent.click(within(form).getByRole("button", { name: "Create case" }));
    expect(within(form).getByRole("alert")).toHaveTextContent("Enter a case code.");
  });

  it("carries an attached audio file to the session it was chosen for, once", async () => {
    const file = new File(["audio"], "visit.wav", { type: "audio/wav" });
    renderThread({ kind: "file", file });

    fireEvent.click(screen.getByRole("button", { name: /Tonkla/ }));
    await waitFor(() => expect(routerPush).toHaveBeenCalled());

    expect(takePendingSessionAudio("another-session")).toBeNull();
    expect(takePendingSessionAudio("session-1")).toBe(file);
    expect(takePendingSessionAudio("session-1")).toBeNull();
  });

  it("says so and keeps the conversation when the session cannot be opened", async () => {
    api.createBackendSessionForCase.mockRejectedValueOnce(new Error("offline"));
    renderThread({ kind: "recording" });

    fireEvent.click(screen.getByRole("button", { name: /Tonkla/ }));

    expect(await screen.findByText("The session could not be opened. Try again.")).toBeInTheDocument();
    expect(routerPush).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/sessions/session-1?view=chat&case_id=case-a&mode=recording"));
  });
});
