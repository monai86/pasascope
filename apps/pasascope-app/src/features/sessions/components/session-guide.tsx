"use client";

import { ArrowRight, MessageCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { sessionMessages } from "@/features/sessions/session.messages";
import { useMessages } from "@/i18n/locale-provider";

/**
 * Conversational "what's next" prompt for the session workspace.
 *
 * Renders like the app speaking to the therapist: a short human prompt in a
 * message bubble, one primary reply-style action, and optional quick-reply
 * chips for alternate paths. Answers the two questions every therapist asks on
 * a session page: "what do I do here?" and "where can I go next?" without
 * adding technical language.
 */
export type SessionGuideAction = {
  label: string;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  reason?: string;
  /** Overrides the default `<guide>-primary` test id for this action. */
  testId?: string;
};

export type SessionGuideQuickReply = {
  label: string;
  href?: string;
  onClick?: () => void;
};

export function SessionGuide({
  prompt,
  primaryAction,
  quickReplies = [],
  testId,
  reasonId: explicitReasonId,
}: {
  prompt: string;
  primaryAction?: SessionGuideAction;
  quickReplies?: SessionGuideQuickReply[];
  testId?: string;
  reasonId?: string;
}) {
  const t = useMessages(sessionMessages).guide;
  const primaryId = testId ? `${testId}-primary` : undefined;
  const reasonId = explicitReasonId ?? (testId ? `${testId}-reason` : undefined);
  const primaryTestId = primaryAction?.testId ?? `${testId}-primary`;
  const hasActions = Boolean(primaryAction) || quickReplies.length > 0;

  return (
    <section
      aria-label={t.label}
      data-testid={testId}
      className="overflow-hidden rounded-panel border border-brand-border bg-brand-soft"
    >
      <div className="flex gap-3 p-3 sm:p-5">
        <span aria-hidden="true" className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-control bg-surface text-brand">
          <MessageCircle size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-brand-strong">{t.eyebrow}</p>
          <p className="mt-1 text-sm font-medium leading-5 text-ink sm:mt-1.5 sm:text-base sm:leading-6">{prompt}</p>
          <div className={hasActions ? "mt-3 flex flex-wrap items-center gap-2" : "hidden"}>
            {primaryAction && primaryAction.href ? (
              <Button
                href={primaryAction.href}
                id={primaryId}
                aria-describedby={primaryAction.disabled ? undefined : reasonId}
                disabled={primaryAction.disabled}
                data-testid={primaryTestId}
              >
                {primaryAction.label}
                <ArrowRight size={16} aria-hidden="true" />
              </Button>
            ) : primaryAction ? (
              <Button
                id={primaryId}
                onClick={primaryAction.onClick}
                disabled={primaryAction.disabled}
                aria-describedby={primaryAction.disabled && primaryAction.reason ? reasonId : undefined}
                data-testid={primaryTestId}
              >
                {primaryAction.label}
                <ArrowRight size={16} aria-hidden="true" />
              </Button>
            ) : null}
            {quickReplies.map((reply) =>
              reply.href ? (
                <Button key={reply.label} href={reply.href} variant="secondary" data-testid={`${testId}-reply-${reply.label}`}>
                  {reply.label}
                </Button>
              ) : (
                <Button key={reply.label} onClick={reply.onClick} variant="secondary" data-testid={`${testId}-reply-${reply.label}`}>
                  {reply.label}
                </Button>
              ),
            )}
          </div>
          {primaryAction && primaryAction.disabled && primaryAction.reason ? (
            <p
              id={reasonId}
              role="status"
              data-testid={`${testId}-reason`}
              className="mt-3 rounded-control border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]"
            >
              {primaryAction.reason}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
