import * as React from "react";

import { cn } from "@/lib/cn";
import { controlClasses } from "@/components/ui/input";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(controlClasses, "min-h-24 py-2.5 leading-6", className)} {...props} />
));
Textarea.displayName = "Textarea";
