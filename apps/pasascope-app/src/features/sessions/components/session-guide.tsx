"use client";

import { ArrowRight } from "lucide-react";

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
      className="overflow-hidden rounded-panel border border-brand-border/70 bg-brand-soft"
    >
      {/* The next step in a sentence, with the button that takes it beside it. */}
      <div className="px-4 py-3.5 sm:px-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
          <p className="min-w-0 text-[15px] font-medium leading-6 text-ink">{prompt}</p>
          <div className={hasActions ? "flex shrink-0 flex-wrap items-center gap-2" : "hidden"}>
            {primaryAction && primaryAction.href ? (
              <Button
                href={primaryAction.href}
                id={primaryId}
                aria-describedby={primaryAction.disabled ? undefined : reasonId}
                disabled={primaryAction.disabled}
                data-testid={primaryTestId}
              >
                <span className="inline-flex items-center gap-2 whitespace-nowrap">
                  {primaryAction.label}
                  <ArrowRight size={16} aria-hidden="true" />
                </span>
              </Button>
            ) : primaryAction ? (
              <Button
                id={primaryId}
                onClick={primaryAction.onClick}
                disabled={primaryAction.disabled}
                aria-describedby={primaryAction.disabled && primaryAction.reason ? reasonId : undefined}
                data-testid={primaryTestId}
              >
                <span className="inline-flex items-center gap-2 whitespace-nowrap">
                  {primaryAction.label}
                  <ArrowRight size={16} aria-hidden="true" />
                </span>
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
    </section>
  );
}
