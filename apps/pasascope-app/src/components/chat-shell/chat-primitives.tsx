import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";

/**
 * The column a conversation is read in. New system lines are announced
 * politely, so a result that arrives while the therapist is elsewhere on the
 * page is not missed and does not interrupt.
 */
export function ChatThread({
  label,
  heading,
  children,
  className,
}: {
  label: string;
  /**
   * The page's top-level heading. A conversation has no visible title of its
   * own on desktop, so it is announced without being shown.
   */
  heading: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <>
      <h1 className="sr-only">{heading}</h1>
      <div
        role="log"
        aria-live="polite"
        aria-label={label}
        className={cn("mx-auto flex w-full max-w-[640px] flex-col gap-6", className)}
      >
        {children}
      </div>
    </>
  );
}

/**
 * Holds the composer at the foot of the page while the conversation scrolls
 * behind it. It spans the page's padding so nothing shows sharp beside the
 * field, and softens what passes under it instead of hiding it.
 */
export function ChatComposerDock({ children }: { children: ReactNode }) {
  return (
    <div className="sticky bottom-0 -mx-4 -mb-4 px-4 pb-4 pt-3 backdrop-blur-md md:-mx-6 md:-mb-6 md:px-6 md:pb-6 lg:-mx-10 lg:px-10">
      {children}
    </div>
  );
}

/** What the therapist said or did, on the right. */
export function UserBubble({ children, testId }: { children: ReactNode; testId?: string }) {
  return (
    <div
      data-testid={testId}
      data-chat-role="user"
      className="max-w-[85%] self-end rounded-[22px] bg-surface px-[18px] py-2.5 shadow-chat-card"
    >
      {children}
    </div>
  );
}

/** What the app says, on the left: plain lines, cards and replies, no bubble. */
export function AssistantMessage({ children, testId }: { children: ReactNode; testId?: string }) {
  return (
    <div data-testid={testId} data-chat-role="assistant" className="flex w-full max-w-[520px] flex-col gap-3">
      {children}
    </div>
  );
}

export function ChatCard({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("overflow-hidden rounded-card bg-surface shadow-chat-card", className)}>{children}</div>;
}

/** A caveat under a card or message. */
export function ChatNote({ children, id }: { children: ReactNode; id?: string }) {
  return <p id={id} className="text-[13px] leading-5 text-ink-subtle">{children}</p>;
}

/** Why a reply cannot be used yet. */
export function ChatBlockedReason({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <p
      id={id}
      role="status"
      className="rounded-control border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-medium text-[color:var(--color-warning-text)]"
    >
      {children}
    </p>
  );
}

export function ChatError({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="rounded-control border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-3 py-2 text-sm font-medium text-[color:var(--color-danger-text)]"
    >
      {children}
    </p>
  );
}

export function QuickReplies({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-2">{children}</div>;
}

type ReplyBaseProps = {
  children: ReactNode;
  /** The one reply that moves the session forward; the others are quiet. */
  primary?: boolean;
  icon?: LucideIcon;
  loading?: boolean;
  disabled?: boolean;
  testId?: string;
  "aria-describedby"?: string;
};

type ReplyButtonProps = ReplyBaseProps & { href?: undefined; onClick: () => void };
type ReplyLinkProps = ReplyBaseProps & { href: string; onClick?: () => void };

/** An answer the therapist can give by pressing it. */
export function QuickReply(props: ReplyButtonProps | ReplyLinkProps) {
  const { children, primary = false, icon: Icon, loading = false, disabled = false, testId } = props;
  const inactive = disabled || loading;
  const classes = cn(
    "inline-flex min-h-[52px] items-center justify-center gap-2 rounded-full font-semibold transition motion-reduce:transition-none",
    FOCUS_RING,
    primary
      ? "bg-action px-7 text-white shadow-chat-action hover:bg-action-hover"
      : "border border-action-quiet-border bg-surface px-5 text-action-quiet-text hover:bg-action-quiet-hover",
    inactive && "cursor-not-allowed opacity-60 shadow-none",
  );
  const content = (
    <>
      {loading ? (
        <Loader2 size={18} aria-hidden="true" className="animate-spin motion-reduce:animate-none" />
      ) : Icon ? (
        <Icon size={18} aria-hidden="true" />
      ) : null}
      <span className="min-w-0">{children}</span>
    </>
  );

  if (props.href) {
    return (
      <Link
        href={props.href}
        onClick={props.onClick}
        data-testid={testId}
        className={cn(classes, inactive && "pointer-events-none")}
        aria-disabled={inactive ? "true" : undefined}
        aria-describedby={props["aria-describedby"]}
        tabIndex={inactive ? -1 : undefined}
      >
        {content}
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={props.onClick}
      disabled={inactive}
      aria-busy={loading || undefined}
      aria-describedby={props["aria-describedby"]}
      data-testid={testId}
      className={classes}
    >
      {content}
    </button>
  );
}
