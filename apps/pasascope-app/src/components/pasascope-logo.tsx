import Link from "next/link";
import React, { useId } from "react";

import { cn } from "@/lib/cn";

interface PasaScopeLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  showWordmark?: boolean;
  showSubtitle?: boolean;
  subtitle?: string;
  href?: string;
}

const markDimensions = {
  xs: { w: 37, h: 24 },
  sm: { w: 50, h: 32 },
  md: { w: 65, h: 42 },
  lg: { w: 87, h: 56 },
  xl: { w: 112, h: 72 },
} as const;

/**
 * The PasaScope mark: a speech bubble (Pasa, "language") examined through a
 * magnifier (Scope). Drawn inline so it takes its colours from the design
 * tokens and stays sharp at every size.
 */
export function PasaScopeLogoMark({
  size = "md",
  className = "",
}: {
  size?: keyof typeof markDimensions;
  className?: string;
}) {
  const dimensions = markDimensions[size];
  // Several marks can be on one page (sidebar and mobile header), so the
  // gradient and mask need ids of their own.
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const gradientId = `pasascope-bubble-${id}`;
  const maskId = `pasascope-gap-${id}`;

  return (
    <svg
      viewBox="0 0 88 56"
      width={dimensions.w}
      height={dimensions.h}
      role="img"
      aria-label="PasaScope Logomark"
      className={cn("shrink-0 select-none", className)}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--color-mark-bubble-from)" />
          <stop offset="1" stopColor="var(--color-mark-bubble-to)" />
        </linearGradient>
        {/* Clears a ring around the lens so it reads as sitting over the bubble. */}
        <mask id={maskId}>
          <rect width="88" height="56" fill="#fff" />
          <circle cx="54" cy="24" r="22" fill="#000" />
        </mask>
      </defs>
      <path
        d="M20 4h10a18 18 0 0 1 18 18v2a18 18 0 0 1-18 18H22l-11 9 2.5-11.6A18 18 0 0 1 2 24v-2A18 18 0 0 1 20 4z"
        fill={`url(#${gradientId})`}
        mask={`url(#${maskId})`}
      />
      <circle cx="54" cy="24" r="17" fill="#fff" stroke="var(--color-highlight)" strokeWidth="5.5" />
      <g stroke="var(--color-highlight)" strokeWidth="3.2" strokeLinecap="round">
        <path d="M44 20v8" />
        <path d="M49 16.5v15" />
        <path d="M54 13v22" />
        <path d="M59 16.5v15" />
        <path d="M64 20v8" />
      </g>
      <path d="M66.5 36.5 80 50" stroke="var(--color-highlight)" strokeWidth="7" strokeLinecap="round" />
    </svg>
  );
}

export function PasaScopeLogo({
  className = "",
  size = "md",
  showWordmark = true,
  showSubtitle = true,
  subtitle = "ภาษา-สโคป",
  href,
}: PasaScopeLogoProps) {
  const sizeConfig = {
    sm: {
      markSize: "sm" as const,
      titleClass: "text-base tracking-tight font-semibold",
      subClass: "text-xs leading-tight font-medium",
      gapClass: "gap-2.5",
    },
    md: {
      markSize: "md" as const,
      titleClass: "text-xl tracking-tight font-semibold",
      subClass: "text-xs leading-tight font-medium",
      gapClass: "gap-3",
    },
    lg: {
      markSize: "lg" as const,
      titleClass: "text-2xl tracking-tight font-semibold",
      subClass: "text-sm leading-tight font-medium",
      gapClass: "gap-3.5",
    },
    xl: {
      markSize: "xl" as const,
      titleClass: "text-4xl tracking-tight font-bold sm:text-5xl",
      subClass: "text-base leading-relaxed font-medium sm:text-lg",
      gapClass: "gap-4 sm:gap-5",
    },
  }[size];

  const content = (
    <div className={cn("inline-flex select-none items-center", sizeConfig.gapClass, className)}>
      <PasaScopeLogoMark size={sizeConfig.markSize} />

      {showWordmark && (
        <div className="flex min-w-0 flex-col">
          <div className={cn("flex items-baseline font-display", sizeConfig.titleClass)}>
            <span className="text-ink">Pasa</span>
            <span className="text-highlight-text">Scope</span>
          </div>
          {showSubtitle && subtitle && (
            <span className={cn("text-ink-muted", sizeConfig.subClass)}>{subtitle}</span>
          )}
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <Link
        href={href}
        className="inline-flex min-h-10 items-center rounded-control opacity-95 transition hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]"
      >
        {content}
      </Link>
    );
  }

  return content;
}
