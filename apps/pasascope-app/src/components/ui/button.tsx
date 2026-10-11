import Link from "next/link";
import { isValidElement } from "react";
import type { LucideIcon } from "lucide-react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "md" | "lg";

// One solid azure primary per view; everything else is secondary or ghost.
const variantClasses: Record<ButtonVariant, string> = {
  primary: "border border-transparent bg-brand text-white shadow-soft hover:bg-brand-hover",
  secondary: "border border-brand-border bg-surface text-brand hover:bg-brand-soft",
  ghost: "border border-transparent bg-transparent text-ink hover:bg-surface-soft",
  danger:
    "border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)] hover:border-[color:var(--color-danger-text)]",
};

const sizeClasses: Record<ButtonSize, string> = {
  md: "min-h-11 px-5 py-2.5 text-sm",
  lg: "min-h-14 px-7 py-3.5 text-base",
};

type BaseProps = {
  children: React.ReactNode;
  icon?: LucideIcon | React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner and blocks activation while an action is in flight. */
  loading?: boolean;
  className?: string;
};

export type ButtonAsButtonProps = BaseProps &
  Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children"> & { href?: undefined };

export type ButtonAsLinkProps = BaseProps &
  Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "children"> & { href: string; disabled?: boolean };

export type ButtonProps = ButtonAsButtonProps | ButtonAsLinkProps;

export function Button(props: ButtonAsButtonProps): React.JSX.Element;
export function Button(props: ButtonAsLinkProps): React.JSX.Element;
export function Button(props: ButtonProps) {
  const { children, icon, variant = "primary", size = "md", loading = false, className } = props;
  const inactive = Boolean(props.disabled) || loading;
  const classes = cn(
    "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] active:scale-[0.99] motion-reduce:transition-none motion-reduce:active:scale-100",
    variantClasses[variant],
    sizeClasses[size],
    inactive && "cursor-not-allowed opacity-60 shadow-none",
    className,
  );

  const content = (
    <>
      {loading ? <Loader2 size={18} aria-hidden="true" className="animate-spin motion-reduce:animate-none" /> : renderIcon(icon)}
      <span className="min-w-0">{children}</span>
    </>
  );

  if ("href" in props && props.href) {
    const { children: _c, className: _cn, disabled, href, icon: _i, size: _s, variant: _v, loading: _l, ...linkProps } = props;
    return (
      <Link
        href={href}
        className={classes}
        aria-disabled={disabled || loading ? "true" : undefined}
        tabIndex={disabled || loading ? -1 : undefined}
        {...linkProps}
      >
        {content}
      </Link>
    );
  }

  const { children: _c, className: _cn, disabled, icon: _i, size: _s, variant: _v, loading: _l, type = "button", ...buttonProps } =
    props as ButtonAsButtonProps;
  return (
    <button type={type} className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...buttonProps}>
      {content}
    </button>
  );
}

function renderIcon(icon: LucideIcon | React.ReactNode | undefined) {
  if (!icon) return null;
  if (isValidElement(icon)) return icon;
  if (typeof icon === "function" || (typeof icon === "object" && "render" in (icon as object))) {
    const Icon = icon as LucideIcon;
    return <Icon size={18} aria-hidden="true" />;
  }
  return icon;
}
