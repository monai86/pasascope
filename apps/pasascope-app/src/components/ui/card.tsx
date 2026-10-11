import * as React from "react";

import { cn } from "@/lib/cn";

export type CardVariant = "plain" | "glass" | "hero";

// `plain` is the white reading surface. `glass` is for chrome only, and `hero`
// is the azure wave card that leads a page with its single next action.
const variantClasses: Record<CardVariant, string> = {
  plain: "rounded-card border border-line bg-surface text-ink shadow-soft",
  glass: "glass-chrome rounded-card text-ink shadow-soft",
  hero: "hero-wave shadow-lift",
};

export function Card({
  className,
  variant = "plain",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: CardVariant }) {
  return <div className={cn(variantClasses[variant], className)} {...props} />;
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1.5 p-5 pb-3", className)} {...props} />;
}

export function CardTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn("text-lg font-semibold leading-snug text-ink", className)} {...props}>
      {children}
    </h3>
  );
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm leading-6 text-ink-muted", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-0", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mt-4 flex items-center border-t border-line p-5", className)} {...props} />;
}
