"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { FolderOpen, Mic, Plus, Upload } from "lucide-react";

import { CaregiverConsentForm } from "@/components/caregiver-consent-form";
import {
  AssistantMessage,
  ChatCard,
  ChatError,
  ChatNote,
  ChatThread,
  QuickReplies,
  QuickReply,
  UserBubble,
} from "@/components/chat-shell/chat-primitives";
import { chatHomeMessages } from "@/features/chat-home/chat-home.messages";
import { caseCode, caseLabel, filterCases, hasConsent } from "@/features/chat-home/chat-home-model";
import { setPendingSessionAudio } from "@/features/sessions/chat/pending-audio";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import { useMessages } from "@/i18n/locale-provider";
import {
  createBackendCase,
  createBackendSessionForCase,
  grantBackendCaseConsent,
  type BackendCase,
} from "@/lib/workflow";
import { loadPreferences } from "@/lib/preferences";

/** How the audio will arrive once the session is open. */
export type StartIntent = "recording" | "audio";

/** What the therapist pressed or typed to begin; it becomes the first bubble. */
export type StartOpener =
  | { kind: "recording" | "audio" | "findCase" | "newSession"; said?: string }
  | { kind: "search"; text: string }
  | { kind: "file"; file: File };

const CASES_SHOWN = 6;
// The limits the Cases form applies to the same fields.
const CASE_CODE_MAX = 64;
const NICKNAME_MAX = 120;
const AGE_MONTHS_MAX = 240;
const FIELD =
  "min-h-11 w-full rounded-control border border-chat-line-strong bg-surface px-4 text-base text-ink outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";

function intentOf(opener: StartOpener): StartIntent | null {
  if (opener.kind === "recording") return "recording";
  if (opener.kind === "audio" || opener.kind === "file") return "audio";
  return null;
}

/**
 * The short conversation that turns "I want to start" into an open session:
 * which case, what to do, the caregiver's consent, then the session itself.
 * A session cannot exist before consent, so this runs on the home screen.
 */
export function StartSessionThread({
  opener,
  cases,
  filter,
  onChoosingCaseChange,
  onCaseCreated,
  onStartOver,
}: {
  opener: StartOpener;
  cases: BackendCase[];
  /** The composer's text, narrowing the case list while one is being chosen. */
  filter: string;
  /** Told whether the case list is on screen, the only time typing does anything here. */
  onChoosingCaseChange?: (choosing: boolean) => void;
  onCaseCreated: () => void;
  onStartOver: () => void;
}) {
  const router = useRouter();
  const t = useMessages(chatHomeMessages);
  const s = t.start;
  const [caseItem, setCaseItem] = useState<BackendCase | null>(null);
  const [creatingCase, setCreatingCase] = useState<{ nickname: string } | null>(null);
  const [intent, setIntent] = useState<StartIntent | null>(() => intentOf(opener));
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentGranted, setConsentGranted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const openerText =
    opener.kind === "search"
      ? opener.text
      : opener.kind === "file"
        ? s.attached(opener.file.name)
        : (opener.said ?? s.intents[opener.kind]);
  const query = filter.trim() || (opener.kind === "search" ? opener.text.trim() : "");
  const matching = filterCases(cases, query);
  const consented = caseItem ? consentGranted || hasConsent(caseItem) : false;
  const choosingCase = !caseItem && !creatingCase;

  useEffect(() => {
    onChoosingCaseChange?.(choosingCase);
  }, [choosingCase, onChoosingCaseChange]);

  async function openSession(target: BackendCase, how: StartIntent) {
    setBusy(true);
    setError("");
    try {
      const session = await createBackendSessionForCase(target.case_id, how === "recording" ? "recording" : "audio-upload", "");
      if (opener.kind === "file") setPendingSessionAudio(session.session_id, opener.file);
      router.push(`${resolveSessionHref("chat", session.session_id, { caseId: target.case_id })}&mode=${how}`);
    } catch {
      setError(s.openFailed);
      setBusy(false);
    }
  }

  function chooseCase(target: BackendCase) {
    setCaseItem(target);
    setCreatingCase(null);
    setError("");
    if (intent && hasConsent(target)) void openSession(target, intent);
  }

  function chooseIntent(how: StartIntent) {
    setIntent(how);
    if (caseItem && consented) void openSession(caseItem, how);
  }

  async function confirmConsent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!caseItem || !intent || !consentChecked || busy) return;
    setBusy(true);
    setError("");
    try {
      await grantBackendCaseConsent(caseItem.case_id, {
        signer: "Parent",
        consentDate: new Date().toISOString().slice(0, 10),
      });
    } catch {
      setError(s.consentFailed);
      setBusy(false);
      return;
    }
    setConsentGranted(true);
    await openSession(caseItem, intent);
  }

  return (
    <ChatThread label={t.threadLabel} heading={t.threadLabel} className="flex-1 pb-6">
      <UserBubble>{openerText}</UserBubble>

      {caseItem ? null : creatingCase ? (
        <NewCaseMessage
          nickname={creatingCase.nickname}
          onCreated={(created) => {
            onCaseCreated();
            chooseCase(created);
          }}
          onCancel={() => setCreatingCase(null)}
        />
      ) : (
        <AssistantMessage testId="start-pick-case">
          <p>
            {cases.length === 0 ? s.noCases : matching.length === 0 ? s.noMatch(query) : query ? s.askCaseFiltered(query) : s.askCase}
          </p>
          {matching.length > 0 ? (
            <ChatCard>
              <ul>
                {matching.slice(0, CASES_SHOWN).map((item) => (
                  <li key={item.case_id} className="border-t border-chat-line first:border-t-0">
                    <button
                      type="button"
                      onClick={() => chooseCase(item)}
                      className="flex min-h-[60px] w-full flex-col justify-center px-[18px] py-2.5 text-left leading-snug transition hover:bg-chat-frame focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
                    >
                      <span className="font-semibold text-ink">{caseLabel(item)}</span>
                      <span className="text-[13px] text-ink-subtle">
                        {caseCode(item)}
                        {hasConsent(item) ? "" : ` · ${s.consentNeeded}`}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </ChatCard>
          ) : null}
          {matching.length > CASES_SHOWN ? <ChatNote>{s.more(matching.length - CASES_SHOWN)}</ChatNote> : null}
          <QuickReplies>
            <QuickReply
              icon={Plus}
              primary={matching.length === 0}
              onClick={() => setCreatingCase({ nickname: matching.length === 0 ? query : "" })}
              testId="start-new-case"
            >
              {matching.length === 0 && query ? s.newCaseFrom(query) : s.newCase}
            </QuickReply>
          </QuickReplies>
        </AssistantMessage>
      )}

      {caseItem ? <UserBubble>{caseLabel(caseItem)}</UserBubble> : null}

      {caseItem && !intent ? (
        <AssistantMessage testId="start-pick-intent">
          <p>{s.askIntent(caseLabel(caseItem))}</p>
          <QuickReplies>
            <QuickReply primary icon={Mic} onClick={() => chooseIntent("recording")}>{s.intents.recording}</QuickReply>
            <QuickReply icon={Upload} onClick={() => chooseIntent("audio")}>{s.intents.audio}</QuickReply>
            <QuickReply icon={FolderOpen} href={`/cases/${encodeURIComponent(caseItem.case_id)}`}>{s.openCase}</QuickReply>
          </QuickReplies>
        </AssistantMessage>
      ) : null}

      {caseItem && intent && opener.kind !== "recording" && opener.kind !== "audio" && opener.kind !== "file" ? (
        <UserBubble>{s.intents[intent]}</UserBubble>
      ) : null}

      {caseItem && intent && !consented ? (
        <AssistantMessage testId="start-consent">
          <p>{s.askConsent}</p>
          <ChatCard className="p-[18px]">
            <CaregiverConsentForm
              busy={busy}
              checked={consentChecked}
              onCheckedChange={setConsentChecked}
              onSubmit={(event) => void confirmConsent(event)}
              submitLabel={s.confirmConsent}
            />
          </ChatCard>
        </AssistantMessage>
      ) : null}

      {caseItem && intent && consented && busy ? (
        <AssistantMessage>
          <p role="status">{s.opening}</p>
        </AssistantMessage>
      ) : null}

      {error ? (
        <AssistantMessage>
          <ChatError>{error}</ChatError>
          {caseItem && intent && consented ? (
            <QuickReplies>
              <QuickReply primary onClick={() => void openSession(caseItem, intent)}>{t.recent.retry}</QuickReply>
            </QuickReplies>
          ) : null}
        </AssistantMessage>
      ) : null}

      <div className="mt-auto pt-2">
        <button
          type="button"
          onClick={onStartOver}
          disabled={busy}
          className="min-h-11 rounded-full px-3 text-sm font-medium text-ink-muted underline-offset-4 transition hover:text-ink hover:underline focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:opacity-60 motion-reduce:transition-none"
        >
          {s.startOver}
        </button>
      </div>
    </ChatThread>
  );
}

function NewCaseMessage({
  nickname: initialNickname,
  onCreated,
  onCancel,
}: {
  nickname: string;
  onCreated: (created: BackendCase) => void;
  onCancel: () => void;
}) {
  const s = useMessages(chatHomeMessages).start;
  const [code, setCode] = useState("");
  const [nickname, setNickname] = useState(initialNickname);
  const [years, setYears] = useState("");
  const [months, setMonths] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const childCode = code.trim();
    if (!childCode) return setError(s.codeRequired);
    if (!years.trim() && !months.trim()) return setError(s.ageRequired);
    const ageMonths = (Number(years) || 0) * 12 + (Number(months) || 0);
    if (
      childCode.length > CASE_CODE_MAX
      || nickname.trim().length > NICKNAME_MAX
      || !Number.isInteger(ageMonths)
      || ageMonths < 0
      || ageMonths > AGE_MONTHS_MAX
    ) {
      return setError(s.createFailed);
    }

    setBusy(true);
    setError("");
    try {
      onCreated(await createBackendCase({
        child_code: childCode,
        nickname: nickname.trim() || undefined,
        age_months: ageMonths,
        language: loadPreferences().caseLanguage,
        notes: "",
        // Consent is asked for next, in the conversation, before any session exists.
        consent_status: "pending",
      }));
    } catch {
      setError(s.createFailed);
      setBusy(false);
    }
  }

  return (
    <AssistantMessage testId="start-new-case-form">
      <p>{s.askNewCase}</p>
      <ChatCard className="p-[18px]">
        <form onSubmit={(event) => void submit(event)} noValidate className="grid gap-4">
          <label className="grid gap-1 text-sm font-medium text-ink">
            {s.caseCode}
            <input className={FIELD} autoComplete="off" value={code} onChange={(event) => setCode(event.target.value)} disabled={busy} />
          </label>
          <label className="grid gap-1 text-sm font-medium text-ink">
            {s.nickname}
            <input className={FIELD} autoComplete="off" value={nickname} onChange={(event) => setNickname(event.target.value)} disabled={busy} />
            <span className="text-[13px] font-normal text-ink-subtle">{s.nicknameHint}</span>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1 text-sm font-medium text-ink">
              {s.ageYears}
              <input className={FIELD} type="number" inputMode="numeric" min="0" max="20" value={years} onChange={(event) => setYears(event.target.value)} disabled={busy} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-ink">
              {s.ageMonths}
              <input className={FIELD} type="number" inputMode="numeric" min="0" max="11" value={months} onChange={(event) => setMonths(event.target.value)} disabled={busy} />
            </label>
          </div>
          {error ? <ChatError>{error}</ChatError> : null}
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={busy}
              className="inline-flex min-h-11 items-center justify-center rounded-full bg-action px-6 font-semibold text-white transition hover:bg-action-hover focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:opacity-60 motion-reduce:transition-none"
            >
              {busy ? s.creatingCase : s.createCase}
            </button>
            <button
              type="button"
              onClick={onCancel}
              disabled={busy}
              className="inline-flex min-h-11 items-center justify-center rounded-full px-5 font-medium text-ink transition hover:bg-chat-frame focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:opacity-60 motion-reduce:transition-none"
            >
              {s.cancel}
            </button>
          </div>
        </form>
      </ChatCard>
    </AssistantMessage>
  );
}
