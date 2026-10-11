import * as React from "react";

import { cn } from "@/lib/cn";
import { controlClasses } from "@/components/ui/input";

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(({ className, children, ...props }, ref) => (
  <select ref={ref} className={cn(controlClasses, "min-h-11 py-2 pr-9", className)} {...props}>
    {children}
  </select>
));
Select.displayName = "Select";
