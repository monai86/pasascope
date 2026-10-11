"use client";

import * as React from "react";

type TabsContextValue = {
  value: string;
  onValueChange: (val: string) => void;
};

const TabsContext = React.createContext<TabsContextValue | null>(null);

export function Tabs({
  value,
  defaultValue,
  onValueChange,
  className = "",
  children,
  ...props
}: {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  className?: string;
  children: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>) {
  const [internalVal, setInternalVal] = React.useState(defaultValue ?? "");
  const currentVal = value !== undefined ? value : internalVal;

  const handleValueChange = React.useCallback(
    (newVal: string) => {
      if (value === undefined) {
        setInternalVal(newVal);
      }
      onValueChange?.(newVal);
    },
    [value, onValueChange]
  );

  return (
    <TabsContext.Provider value={{ value: currentVal, onValueChange: handleValueChange }}>
      <div className={`w-full ${className}`} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  className = "",
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="tablist"
      className={`inline-flex items-center gap-1 rounded-full border border-line bg-surface-muted p-1 text-ink-muted ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  className = "",
  children,
  disabled = false,
  ...props
}: {
  value: string;
  className?: string;
  children: React.ReactNode;
  disabled?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const ctx = React.useContext(TabsContext);
  const isSelected = ctx?.value === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isSelected}
      disabled={disabled}
      onClick={() => ctx?.onValueChange(value)}
      className={`inline-flex min-h-11 items-center justify-center rounded-full px-4 py-1.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:pointer-events-none disabled:opacity-50 motion-reduce:transition-none ${
        isSelected ? "bg-surface text-brand shadow-soft" : "hover:text-ink"
      } ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  className = "",
  children,
  ...props
}: {
  value: string;
  className?: string;
  children: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>) {
  const ctx = React.useContext(TabsContext);
  if (ctx?.value !== value) return null;

  return (
    <div
      role="tabpanel"
      tabIndex={0}
      className={`mt-4 rounded-control focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
