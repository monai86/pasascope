"use client";

import type { LucideIcon } from "lucide-react";
import { ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useSafetyCopy } from "@/lib/safety-copy";

type IconTone = "brand" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<IconTone, string> = {
  brand: "text-brand",
  success: "text-[color:var(--color-success-text)]",
  warning: "text-[color:var(--color-warning-text)]",
  danger: "text-[color:var(--color-danger-text)]",
  info: "text-[color:var(--color-info-text)]"
};

export function WorkspacePanel({
  children,
  className = "",
  ...props
}: {
  children: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLElement>) {
  return <section className={`workspace-panel ${className}`} {...props}>{children}</section>;
}

export function PrimaryActionButton({
  children,
  href,
  icon,
  className = "",
  disabled = false,
  type = "button",
  ...props
}: {
  children: React.ReactNode;
  href?: string;
  icon?: LucideIcon;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
} & React.ButtonHTMLAttributes<HTMLButtonElement> & React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  return href ? (
    <Button href={href} icon={icon} className={className} {...(props as React.AnchorHTMLAttributes<HTMLAnchorElement>)}>
      {children}
    </Button>
  ) : (
    <Button icon={icon} className={className} disabled={disabled} type={type} {...(props as React.ButtonHTMLAttributes<HTMLButtonElement>)}>
      {children}
    </Button>
  );
}

export function SafetyNote({ children }: { children?: React.ReactNode }) {
  const safety = useSafetyCopy();

  return (
    <p className="flex items-center justify-center gap-2 px-2 py-3 text-center text-xs font-medium text-ink-subtle">
      <ShieldCheck size={16} aria-hidden="true" className="shrink-0 text-brand" />
      {children ?? safety.SAFETY_NOTICE_DEFAULT}
    </p>
  );
}

export function WorkflowStep({ icon: Icon, title, helper, tone = "brand" }: { icon: LucideIcon; title: string; helper: string; tone?: IconTone }) {
  return (
    <div className="flex flex-1 flex-col items-center text-center">
      <span className={`mb-2 flex h-10 w-10 items-center justify-center ${toneClasses[tone]}`}>
        <Icon size={22} aria-hidden="true" />
      </span>
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="mt-0.5 text-xs text-ink-subtle">{helper}</p>
    </div>
  );
}
