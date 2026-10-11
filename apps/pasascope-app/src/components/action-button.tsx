import type { LucideIcon } from "lucide-react";

import { Button, type ButtonVariant } from "@/components/ui/button";
import { cn } from "@/lib/cn";

type ActionButtonTone = "primary" | "secondary" | "ghost" | "destructive";
type ActionButtonSize = "md" | "lg";

const variantByTone: Record<ActionButtonTone, ButtonVariant> = {
  primary: "primary",
  secondary: "secondary",
  ghost: "ghost",
  destructive: "danger",
};

type BaseProps = {
  children: React.ReactNode;
  icon?: LucideIcon | React.ReactNode;
  tone?: ActionButtonTone;
  size?: ActionButtonSize;
  className?: string;
};

type ButtonProps = BaseProps & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  href?: undefined;
};

type LinkProps = BaseProps & Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "children"> & {
  href: string;
  disabled?: boolean;
};

/**
 * The workbench's action button: full width on a phone, natural width from
 * `sm` up. It is the shared Button with that layout default.
 */
export function ActionButton(props: ButtonProps): React.JSX.Element;
export function ActionButton(props: LinkProps): React.JSX.Element;
export function ActionButton({ tone = "primary", className, ...props }: ButtonProps | LinkProps) {
  const classes = cn("w-full sm:w-auto", className);
  return "href" in props && props.href ? (
    <Button variant={variantByTone[tone]} className={classes} {...(props as LinkProps)} />
  ) : (
    <Button variant={variantByTone[tone]} className={classes} {...(props as ButtonProps)} />
  );
}
