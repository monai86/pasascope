import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionChatView, type SessionChatViewProps } from "@/features/sessions/chat/session-chat-view";
import { createInitialWorkflowState, type FeatureSignal, type TranscriptLine, type WorkflowState } from "@/lib/workflow";

const settings = vi.hoisted(() => ({ external: false }));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: {
      auth_mode: "mock",
      access_model: { public_signup: true, review_gates: "open" },
      pipeline_settings: { transcription_external: settings.external },
    },
  }),
}));

function line(lineId: string, speaker: string, text = "words here"): TranscriptLine {
  return { lineId, speaker, text };
}

function signal(featureName: string, rawValue: number): FeatureSignal {
  return {
    featureName,
    displayName: featureName,
    description: "",
    valueType: "float",
    unit: "",
    value: String(rawValue),
    rawValue,
    calculationMethod: "",
    requiredInputs: [],
    limitations: [],
    clinicalInterpretationCaution: "",
    interpretationHint: "",
    referenceText: "",
  };
}

const complete = [line("1", "THER"), line("2", "CHI"), line("3", "THER")];
const mixed = [line("1", "THER"), line("2", "CHI"), line("3", "UNK"), line("4", "")];

function workflow(overrides: Partial<WorkflowState> = {}): WorkflowState {
  return { ...createInitialWorkflowState(), workflowLoading: false, backendSessionId: "s1", sessionId: "s1", ...overrides };
}

function withTranscript(lines: TranscriptLine[], overrides: Partial<WorkflowState> = {}): WorkflowState {
  return workflow({ transcriptReady: true, transcriptLines: lines, transcriptSaveStatus: "saved", ...overrides });
}

function props(overrides: Partial<SessionChatViewProps> = {}): SessionChatViewProps {
  return {
    sessionContext: {
      sessionId: "s1",
      caseId: "case-1",
      caseLabel: "C-1001",
      consentStatus: "granted",
      dataMode: "backend",
      activeView: "intake",
    },
    state: workflow(),
    hydrated: true,
    busy: false,
    backendUnavailable: false,
    source: "audio",
    lines: [],
    notes: "",
    summary: {},
    attachError: "",
    audio: { recorded: null, step: "idle", jobStatus: "queued", jobMessage: "" },
    hrefs: { transcript: "/sessions/s1?view=transcript", findings: "/sessions/s1?view=findings", report: "/sessions/s1?view=report" },
    onRecordingMetadata: vi.fn(),
    onRecordingReady: vi.fn(),
    onAudioFile: vi.fn(),
    onDiscardAudio: vi.fn(),
    onUploadAudio: vi.fn(),
    onAttachTranscript: vi.fn(),
    onAssignUnknownSpeakers: vi.fn(),
    onRetrySave: vi.fn(),
    onExtractMeasures: vi.fn(),
    onGenerateReport: vi.fn(),
    onSaveNote: vi.fn().mockResolvedValue(true),
    ...overrides,
  };
}

function recorded(sizeBytes: number) {
  return { blob: new Blob([new Uint8Array(sizeBytes)]), durationSeconds: 728 };
}

afterEach(() => {
  settings.external = false;
});

describe("session conversation view", () => {
  it("asks for an audio file and says which formats it takes", () => {
    render(<SessionChatView {...props()} />);

    const ask = screen.getByTestId("chat-ask-audio");
    expect(within(ask).getByRole("button", { name: "Choose an audio file" })).toBeInTheDocument();
    expect(within(ask).getByText("WAV, MP3, M4A, MP4, WebM or OGG")).toBeInTheDocument();
  });

  it("collects nothing while consent is not active", () => {
    render(<SessionChatView {...props({ sessionContext: { ...props().sessionContext, consentStatus: "withdrawn" } })} />);

    expect(screen.getByTestId("chat-consent-inactive")).toBeInTheDocument();
    expect(screen.queryByTestId("chat-ask-audio")).toBeNull();
    expect(screen.queryByRole("button", { name: "Attach an audio file or a .cha transcript" })).toBeNull();
  });

  it("says the audio goes to an external service before it is sent", () => {
    settings.external = true;
    const view = props({ audio: { recorded: recorded(1024), step: "confirm", jobStatus: "queued", jobMessage: "" } });
    render(<SessionChatView {...view} />);

    const confirm = screen.getByTestId("chat-confirm-upload");
    expect(within(confirm).getByText(/sent to an external transcription service/)).toBeInTheDocument();
    expect(within(confirm).getByText(/has not been clinically validated|experimental/i)).toBeInTheDocument();
    expect(view.onUploadAudio).not.toHaveBeenCalled();

    fireEvent.click(within(confirm).getByRole("button", { name: "Send for transcription" }));
    expect(view.onUploadAudio).toHaveBeenCalledTimes(1);
  });

  it("says the audio goes to this deployment's server when transcription is on-device", () => {
    render(<SessionChatView {...props({ audio: { recorded: recorded(1024), step: "confirm", jobStatus: "queued", jobMessage: "" } })} />);

    const confirm = screen.getByTestId("chat-confirm-upload");
    expect(within(confirm).getByText(/sent to the backend for transcription/)).toBeInTheDocument();
    expect(within(confirm).queryByText(/external transcription service/)).toBeNull();
  });

  it("will not send a file the hosted service would refuse", () => {
    settings.external = true;
    render(
      <SessionChatView
        {...props({ audio: { recorded: recorded(26 * 1024 * 1024), step: "confirm", jobStatus: "queued", jobMessage: "" } })}
      />,
    );

    expect(screen.getByText(/larger than 25 MB/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send for transcription" })).toBeDisabled();
  });

  it("sets the remaining speakers when the therapist says who they are", () => {
    const view = props({ state: withTranscript(mixed), lines: mixed });
    render(<SessionChatView {...view} />);

    expect(screen.getByText(/2 lines still have no speaker/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "The rest are the therapist" }));
    expect(view.onAssignUnknownSpeakers).toHaveBeenCalledWith("THER");
  });

  it("offers only the transcript when no line has a speaker", () => {
    const unknown = [line("1", "UNK"), line("2", "UNK")];
    render(<SessionChatView {...props({ state: withTranscript(unknown), lines: unknown })} />);

    expect(screen.queryByRole("button", { name: "The rest are the therapist" })).toBeNull();
    expect(screen.queryByRole("button", { name: "The rest are the child" })).toBeNull();
    expect(screen.getByTestId("reply-open-transcript")).toHaveAttribute("href", "/sessions/s1?view=transcript");
  });

  it("explains why the measures cannot be extracted when no line is the child's", () => {
    const noChild = [line("1", "THER"), line("2", "THER")];
    const view = props({ state: withTranscript(noChild), lines: noChild });
    render(<SessionChatView {...view} />);

    const extract = screen.getByRole("button", { name: "Extract the language measures" });
    expect(extract).toBeDisabled();
    const reason = document.getElementById(extract.getAttribute("aria-describedby") ?? "");
    expect(reason).toHaveTextContent("No line is marked as the child's yet.");
  });

  it("extracts the measures when asked", () => {
    const view = props({ state: withTranscript(complete), lines: complete });
    render(<SessionChatView {...view} />);

    fireEvent.click(screen.getByRole("button", { name: "Extract the language measures" }));
    expect(view.onExtractMeasures).toHaveBeenCalledTimes(1);
  });

  it("shows the backend's measures with the reminder that they are for the therapist to interpret", () => {
    const state = withTranscript(complete, {
      analysisStatus: "completed",
      featuresExtracted: true,
      featureSignals: [
        signal("mean_length_of_utterance_words", 2.8),
        signal("total_word_count", 129),
        signal("number_of_different_words", 61),
        signal("child_utterance_count", 46),
      ],
    });
    render(<SessionChatView {...props({ state, lines: complete })} />);

    const measures = screen.getByTestId("chat-measures");
    expect(within(measures).getByText(/from 46 child utterances/)).toBeInTheDocument();
    expect(within(measures).getByTestId("measure-mlu")).toHaveTextContent("2.8");
    expect(within(measures).getByTestId("measure-total-words")).toHaveTextContent("129");
    expect(within(measures).getByTestId("measure-distinct-words")).toHaveTextContent("61");
    expect(within(measures).getByText(/Therapist interpretation required\./)).toBeInTheDocument();
    expect(within(measures).getByRole("button", { name: "Draft the report" })).toBeEnabled();
  });

  it("shows a blank, never a number, for a measure the backend did not send", () => {
    const state = withTranscript(complete, { analysisStatus: "completed", featuresExtracted: true, featureSignals: [] });
    render(<SessionChatView {...props({ state, lines: complete })} />);

    for (const id of ["measure-mlu", "measure-total-words", "measure-distinct-words"]) {
      const value = screen.getByTestId(id);
      expect(value).toHaveTextContent("No value");
      expect(value.textContent).not.toMatch(/\d/);
    }
  });

  it("saves typed text as a session note and never treats it as a command", async () => {
    const view = props({ state: withTranscript(complete), lines: complete });
    render(<SessionChatView {...view} />);

    fireEvent.change(screen.getByRole("textbox", { name: "Session note" }), {
      target: { value: "Draft the report after lunch" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save note" }));

    await waitFor(() => expect(view.onSaveNote).toHaveBeenCalledWith("Draft the report after lunch"));
    expect(screen.getByTestId("chat-note")).toHaveTextContent("Draft the report after lunch");
    expect(await screen.findByText(/Saved as a session note/)).toBeInTheDocument();
    // The words name an action, but only a pressed reply runs one.
    expect(view.onGenerateReport).not.toHaveBeenCalled();
    expect(view.onExtractMeasures).not.toHaveBeenCalled();
  });

  it("says so when a note could not be saved", async () => {
    const view = props({ onSaveNote: vi.fn().mockResolvedValue(false) });
    render(<SessionChatView {...view} />);

    fireEvent.change(screen.getByRole("textbox", { name: "Session note" }), { target: { value: "note" } });
    fireEvent.click(screen.getByRole("button", { name: "Save note" }));

    expect(await screen.findByText("The note could not be saved.")).toBeInTheDocument();
  });

  it("opens the report draft once one exists", () => {
    const state = withTranscript(complete, {
      analysisStatus: "completed",
      featuresExtracted: true,
      reportStatus: "draft",
      reportSaveStatus: "saved",
    });
    render(<SessionChatView {...props({ state, lines: complete })} />);

    expect(screen.getByTestId("reply-open-report")).toHaveAttribute("href", "/sessions/s1?view=report");
    expect(screen.queryByRole("button", { name: "Draft the report" })).toBeNull();
  });
});
