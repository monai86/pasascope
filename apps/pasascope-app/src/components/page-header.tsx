export function PageHeader({
  title,
  description,
  eyebrow = "",
  meta = [],
  actions
}: {
  title: string;
  description: string;
  eyebrow?: string;
  meta?: string[];
  actions?: React.ReactNode;
}) {
  return (
    <header className="mb-8 border-b border-line pb-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          {eyebrow ? (
            <p className="mb-3 inline-flex min-h-8 items-center rounded-full border border-brand-border bg-brand-soft px-3.5 py-1 text-xs font-semibold text-brand shadow-2xs">
              <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-highlight" />
              {eyebrow}
            </p>
          ) : null}
          <h1 className="text-3xl font-bold tracking-tight text-ink sm:text-4xl">{title}</h1>
          <p className="mt-2 max-w-[70ch] text-sm leading-6 text-ink-muted">{description}</p>
          {meta.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {meta.map((item) => (
                <span
                  key={item}
                  className="inline-flex min-h-7 items-center rounded-full border border-line bg-surface px-3 text-xs font-medium text-ink-muted shadow-2xs"
                >
                  {item}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
    </header>
  );
}
