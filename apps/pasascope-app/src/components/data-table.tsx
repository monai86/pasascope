type DataTableColumn<T extends Record<string, React.ReactNode>> = {
  key: keyof T;
  header: string;
  align?: "left" | "right";
};

export function DataTable<T extends Record<string, React.ReactNode>>({
  caption,
  columns,
  rows,
  selectedId,
  onSelect,
  rowTestId
}: {
  caption: string;
  columns: DataTableColumn<T>[];
  rows: Array<T & { id: string }>;
  /** Optional row selection (Airtable-style): the selected row is highlighted and announced. */
  selectedId?: string;
  onSelect?: (id: string) => void;
  /** Optional data-testid applied to every body row (e.g. for e2e row assertions). */
  rowTestId?: string;
}) {
  return (
    <div className="reading-surface overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse" aria-label={caption}>
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-line bg-surface-muted text-left">
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  scope="col"
                  className={`px-4 py-3 text-[13px] font-semibold text-ink-muted ${
                    column.align === "right" ? "text-right" : "text-left"
                  }`}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const selected = row.id === selectedId;
              const selectable = Boolean(onSelect);
              return (
                <tr
                  key={row.id}
                  data-testid={rowTestId}
                  aria-selected={selectable ? selected : undefined}
                  onClick={selectable ? () => onSelect?.(row.id) : undefined}
                  className={`border-b border-line last:border-b-0 ${
                    selectable ? "cursor-pointer" : ""
                  } ${
                    selected
                      ? "bg-brand-soft"
                      : selectable
                        ? "transition-colors hover:bg-surface-muted"
                        : ""
                  }`}
                >
                  {columns.map((column) => (
                    <td
                      key={String(column.key)}
                      className={`px-4 py-3 text-sm text-ink ${
                        column.align === "right" ? "text-right" : "text-left"
                      }`}
                    >
                      {row[column.key]}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
