"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Check, Mic, Pause, Play, RotateCcw, Square, Trash2 } from "lucide-react";

import { audioCaptureMessages } from "@/components/audio-capture.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useAppMode } from "@/lib/app-mode";

export type RecordingMetadata = {
  recordingStatus: "idle" | "recording" | "paused" | "stopped" | "interrupted" | "error";
  durationSeconds: number;
  mimeType?: string;
  createdAt?: string;
  hasUnsavedRecording: boolean;
  error?: string;
};

type BrowserAudioRecorderProps = {
  initialDurationSeconds: number;
  hadUnsavedRecording: boolean;
  onMetadataChange: (metadata: RecordingMetadata) => void;
  onRecordingReady?: (blob: Blob, metadata: RecordingMetadata) => void;
  onRecordingCleared?: () => void;
};

export function BrowserAudioRecorder({
  initialDurationSeconds,
  hadUnsavedRecording,
  onMetadataChange,
  onRecordingReady,
  onRecordingCleared
}: BrowserAudioRecorderProps) {
  const [status, setStatus] = useState<RecordingMetadata["recordingStatus"]>("idle");
  const [durationSeconds, setDurationSeconds] = useState(initialDurationSeconds);
  const [audioUrl, setAudioUrl] = useState("");
  const [error, setError] = useState("");
  const t = useMessages(audioCaptureMessages).recorder;
  const { externalTranscription } = useAppMode();
  const [privacyNotice, setPrivacyNotice] = useState(hadUnsavedRecording);
  const [amplitudes, setAmplitudes] = useState<number[]>(() => Array.from({ length: 24 }, () => 8));
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioBlobRef = useRef<Blob | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | undefined>(undefined);
  const animationRef = useRef<number | undefined>(undefined);
  const audioContextRef = useRef<AudioContext | null>(null);
  const trackEndedHandlerRef = useRef<(() => void) | null>(null);
  const durationRef = useRef(initialDurationSeconds);
  const statusRef = useRef(status);
  const audioUrlRef = useRef("");
  const createdAtRef = useRef<string | undefined>(undefined);
  const mimeTypeRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    durationRef.current = durationSeconds;
  }, [durationSeconds]);

  useEffect(() => {
    if (statusRef.current !== "idle" || audioUrlRef.current) return;
    setDurationSeconds(initialDurationSeconds);
    durationRef.current = initialDurationSeconds;
  }, [initialDurationSeconds]);

  useEffect(() => {
    if (hadUnsavedRecording) setPrivacyNotice(true);
  }, [hadUnsavedRecording]);

  useEffect(() => () => {
    clearTimer();
    stopVisualization();
    stopStream();
    revokeAudioUrl();
  }, []);

  async function startRecording() {
    setError("");
    setPrivacyNotice(false);
    revokeAudioUrl();
    setDurationSeconds(0);
    durationRef.current = 0;

    if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      fail(t.errors.unsupported);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mimeType = selectMimeType();
      const recorder = mimeType ? new window.MediaRecorder(stream, { mimeType }) : new window.MediaRecorder(stream);
      recorderRef.current = recorder;
      const createdAt = new Date().toISOString();
      createdAtRef.current = createdAt;
      mimeTypeRef.current = recorder.mimeType || mimeType || "audio/webm";

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => interruptRecording(t.errors.interrupted);
      recorder.onstop = () => finalizeRecording(recorder.mimeType || mimeType || "audio/webm", createdAt);
      attachTrackEndedHandler(stream);
      recorder.start(250);
      setStatus("recording");
      statusRef.current = "recording";
      startTimer();
      startVisualization(stream);
      onMetadataChange({
        recordingStatus: "recording",
        durationSeconds: 0,
        mimeType: recorder.mimeType || mimeType,
        createdAt,
        hasUnsavedRecording: true
      });
    } catch (cause) {
      const message = cause instanceof DOMException && (cause.name === "NotAllowedError" || cause.name === "SecurityError")
        ? t.errors.permissionDenied
        : t.errors.notStarted;
      fail(message);
    }
  }

  function pauseRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "recording") return;
    recorder.pause();
    clearTimer();
    setStatus("paused");
    statusRef.current = "paused";
    onMetadataChange(currentMetadata("paused", true));
  }

  function resumeRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "paused") return;
    recorder.resume();
    setStatus("recording");
    statusRef.current = "recording";
    startTimer();
    onMetadataChange(currentMetadata("recording", true));
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    clearTimer();
    stopVisualization();
    recorder.stop();
  }

  function deleteRecording() {
    resetRecording();
    onRecordingCleared?.();
    onMetadataChange({
      recordingStatus: "idle",
      durationSeconds: 0,
      hasUnsavedRecording: false
    });
  }

  async function rerecord() {
    resetRecording();
    await startRecording();
  }

  function resetRecording() {
    clearTimer();
    stopVisualization();
    stopStream();
    recorderRef.current = null;
    chunksRef.current = [];
    audioBlobRef.current = null;
    revokeAudioUrl();
    setDurationSeconds(0);
    durationRef.current = 0;
    setStatus("idle");
    statusRef.current = "idle";
    setError("");
    setPrivacyNotice(false);
    createdAtRef.current = undefined;
    mimeTypeRef.current = undefined;
  }

  function finalizeRecording(mimeType: string, createdAt: string) {
    clearTimer();
    stopVisualization();
    stopStream();
    const blob = new Blob(chunksRef.current, { type: mimeType });
    chunksRef.current = [];
    recorderRef.current = null;
    if (blob.size === 0) {
      fail(t.errors.empty);
      return;
    }
    audioBlobRef.current = blob;
    const url = URL.createObjectURL(blob);
    audioUrlRef.current = url;
    setAudioUrl(url);
    setStatus("stopped");
    statusRef.current = "stopped";
    const metadata: RecordingMetadata = {
      recordingStatus: "stopped",
      durationSeconds: durationRef.current,
      mimeType,
      createdAt,
      hasUnsavedRecording: true
    };
    onMetadataChange(metadata);
    onRecordingReady?.(blob, metadata);
  }

  function interruptRecording(message: string) {
    if (statusRef.current !== "recording" && statusRef.current !== "paused") return;
    clearTimer();
    stopVisualization();
    stopStream();
    recorderRef.current = null;
    chunksRef.current = [];
    setStatus("interrupted");
    statusRef.current = "interrupted";
    setError(message);
    onMetadataChange({
      recordingStatus: "interrupted",
      durationSeconds: durationRef.current,
      hasUnsavedRecording: false,
      error: message
    });
  }

  function fail(message: string) {
    clearTimer();
    stopVisualization();
    stopStream();
    setStatus("error");
    statusRef.current = "error";
    setError(message);
    onMetadataChange({
      recordingStatus: "error",
      durationSeconds: durationRef.current,
      hasUnsavedRecording: false,
      error: message
    });
  }

  function startTimer() {
    clearTimer();
    timerRef.current = window.setInterval(() => {
      durationRef.current += 1;
      setDurationSeconds(durationRef.current);
      onMetadataChange(currentMetadata("recording", true));
    }, 1000);
  }

  function clearTimer() {
    if (timerRef.current !== undefined) {
      window.clearInterval(timerRef.current);
      timerRef.current = undefined;
    }
  }

  function attachTrackEndedHandler(stream: MediaStream) {
    const track = stream.getAudioTracks()[0];
    if (!track) return;
    const handler = () => interruptRecording(t.errors.interrupted);
    trackEndedHandlerRef.current = handler;
    track.addEventListener("ended", handler);
  }

  function stopStream() {
    const stream = streamRef.current;
    if (!stream) return;
    const track = stream.getAudioTracks()[0];
    if (track && trackEndedHandlerRef.current) track.removeEventListener("ended", trackEndedHandlerRef.current);
    stream.getTracks().forEach((item) => item.stop());
    streamRef.current = null;
    trackEndedHandlerRef.current = null;
  }

  function startVisualization(stream: MediaStream) {
    if (typeof window.AudioContext === "undefined") {
      setAmplitudes(Array.from({ length: 24 }, (_, index) => 12 + ((index * 17) % 42)));
      return;
    }
    const context = new window.AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 64;
    context.createMediaStreamSource(stream).connect(analyser);
    const values = new Uint8Array(analyser.frequencyBinCount);
    audioContextRef.current = context;
    const draw = () => {
      analyser.getByteFrequencyData(values);
      setAmplitudes(Array.from({ length: 24 }, (_, index) => Math.max(8, Math.round((values[index] / 255) * 76))));
      animationRef.current = window.requestAnimationFrame(draw);
    };
    draw();
  }

  function stopVisualization() {
    if (animationRef.current !== undefined) window.cancelAnimationFrame(animationRef.current);
    animationRef.current = undefined;
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    setAmplitudes(Array.from({ length: 24 }, () => 8));
  }

  function revokeAudioUrl() {
    if (!audioUrlRef.current) return;
    URL.revokeObjectURL?.(audioUrlRef.current);
    audioUrlRef.current = "";
    setAudioUrl("");
  }

  function currentMetadata(recordingStatus: RecordingMetadata["recordingStatus"], hasUnsavedRecording: boolean): RecordingMetadata {
    return {
      recordingStatus,
      durationSeconds: durationRef.current,
      mimeType: mimeTypeRef.current,
      createdAt: createdAtRef.current,
      hasUnsavedRecording
    };
  }

  const statusText = t.status[status === "error" ? "idle" : status];
  const live = status === "recording";
  const held = status === "paused";
  // Waiting to start: the bars breathe in a slow wave, so the card reads as ready.
  const waiting = !live && !held && !audioUrl;
  const roundButton =
    "relative grid place-items-center rounded-full transition motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";
  const mainButton = `${roundButton} z-10 h-[72px] w-[72px] bg-action text-white shadow-chat-action hover:bg-action-hover active:scale-[0.96]`;

  return (
    <div className="flex flex-col items-center text-center" data-recorder-state={status}>
      <p
        className={`inline-flex min-h-8 items-center gap-2 rounded-full px-3 text-[13px] font-semibold ${
          live ? "bg-highlight-soft text-highlight-text" : "bg-surface-muted text-ink-muted"
        }`}
      >
        <span aria-hidden="true" className={`h-2 w-2 rounded-full ${live ? "recorder-dot bg-highlight" : held ? "bg-ink-subtle" : "bg-brand"}`} />
        {statusText}
      </p>

      <p className="mt-3 font-display text-[2.75rem] font-semibold leading-none tracking-[-0.01em] text-ink tabular-nums">
        {formatDuration(durationSeconds)}
      </p>

      <div className="mt-6 flex h-16 w-full max-w-[22rem] items-center justify-center gap-[5px]" role="img" aria-label={t.amplitude}>
        {amplitudes.map((height, index) => (
          <span
            key={index}
            aria-hidden="true"
            className={`recorder-bar h-16 w-[5px] rounded-full ${waiting ? "recorder-bar-waiting bg-tint-strong" : live ? "bg-brand" : "bg-line-strong"}`}
            style={{ "--i": index, transform: waiting ? undefined : `scaleY(${Math.max(0.12, height / 76)})` } as CSSProperties}
          />
        ))}
      </div>

      {/* Three columns, so the main button sits on the centre line and stop sits beside it. */}
      <div className="mt-7 grid grid-cols-[3.5rem_4.5rem_3.5rem] items-center justify-center gap-4">
        <span aria-hidden="true" />
        {/* Rings spread from the button while the microphone is on, as they do from the mark. */}
        <span className="relative grid h-[72px] w-[72px] place-items-center">
          {live ? (
            <>
              <span aria-hidden="true" className="recorder-ring" />
              <span aria-hidden="true" className="recorder-ring" />
            </>
          ) : null}
          {status === "idle" || status === "error" || status === "interrupted" ? (
            <button type="button" className={mainButton} aria-label={t.start} onClick={startRecording}>
              <Mic size={28} aria-hidden="true" />
            </button>
          ) : null}
          {live ? (
            <button type="button" className={mainButton} aria-label={t.pause} onClick={pauseRecording}>
              <Pause size={26} fill="currentColor" aria-hidden="true" />
            </button>
          ) : null}
          {held ? (
            <button type="button" className={mainButton} aria-label={t.resume} onClick={resumeRecording}>
              <Play size={26} fill="currentColor" aria-hidden="true" />
            </button>
          ) : null}
          {status === "stopped" ? (
            <span aria-hidden="true" className="grid h-[72px] w-[72px] place-items-center rounded-full bg-brand-soft text-brand">
              <Check size={28} />
            </span>
          ) : null}
        </span>
        <button
          type="button"
          className={`${roundButton} h-14 w-14 border border-action-quiet-border bg-surface text-action-quiet-text hover:bg-action-quiet-hover disabled:pointer-events-none disabled:opacity-35`}
          aria-label={t.stop}
          onClick={stopRecording}
          disabled={status !== "recording" && status !== "paused"}
        >
          <Square size={18} fill="currentColor" aria-hidden="true" />
        </button>
      </div>

      {audioUrl ? (
        <div className="recorder-playback mt-6 w-full rounded-control border border-line bg-surface-muted p-3">
          <audio className="w-full" controls src={audioUrl} aria-label={t.playback} />
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-action-quiet-border bg-surface px-4 text-sm font-semibold text-action-quiet-text transition hover:bg-action-quiet-hover motion-reduce:transition-none" onClick={rerecord}>
              <RotateCcw size={16} aria-hidden="true" />
              {t.rerecord}
            </button>
            <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-[color:var(--color-danger-border)] bg-surface px-4 text-sm font-semibold text-[color:var(--color-danger-text)] transition hover:bg-[color:var(--color-danger-bg)] motion-reduce:transition-none" onClick={deleteRecording} aria-label={t.deleteLabel}>
              <Trash2 size={16} aria-hidden="true" />
              {t.delete}
            </button>
          </div>
        </div>
      ) : null}

      {privacyNotice && waiting ? <p className="mt-5 w-full rounded-control border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-4 py-3 text-left text-sm font-medium text-[color:var(--color-warning-text)]">{t.clearedForPrivacy}</p> : null}
      {error ? <p className="mt-5 w-full rounded-control border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-4 py-3 text-left text-sm font-medium text-[color:var(--color-danger-text)]" role="alert">{error}</p> : null}

      <div className="mt-6 w-full border-t border-line pt-4 text-left">
        <p className="text-[13px] leading-5 text-ink-muted">{externalTranscription ? t.experimentalExternal : t.experimental}</p>
        <p className="mt-1 text-[13px] leading-5 text-ink-subtle">{t.memoryOnly}</p>
      </div>
    </div>
  );
}

function selectMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find((type) => window.MediaRecorder.isTypeSupported?.(type)) ?? "";
}

function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return [hours, minutes, remainder].map((part) => String(part).padStart(2, "0")).join(":");
}
