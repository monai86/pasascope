"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { LogOut, RefreshCw, Search } from "lucide-react";

import { ActiveOrganizationSummary } from "@/components/active-organization-summary";
import { LanguageToggle } from "@/components/language-toggle";
import { shellMessages } from "@/components/shell.messages";
import { Button } from "@/components/ui/button";
import { useMessages } from "@/i18n/locale-provider";
import { useShellUser } from "@/components/use-shell-user";
import { useAppMode } from "@/lib/app-mode";

export function Topbar({ showSearch = true }: { /** Off where the page has its own case search. */ showSearch?: boolean } = {}) {
  const router = useRouter();
  const t = useMessages(shellMessages);
  const [query, setQuery] = useState("");
  const { publicSignup } = useAppMode();
  const user = useShellUser();

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    router.push(trimmed ? `/cases?q=${encodeURIComponent(trimmed)}` : "/cases");
  }

  return (
    <header className="glass-chrome sticky top-0 z-20 hidden min-w-0 border-x-0 border-t-0 px-6 py-3 lg:flex lg:items-center lg:justify-between lg:gap-4">
      {showSearch ? (
        <form
          role="search"
          onSubmit={handleSearch}
          className="hidden min-h-11 min-w-0 max-w-md flex-1 items-center gap-2.5 rounded-full border border-line bg-surface px-4 transition focus-within:border-brand focus-within:ring-4 focus-within:ring-[color:var(--color-focus-ring)] xl:flex"
        >
          <Search size={17} aria-hidden="true" className="shrink-0 text-ink-subtle" />
          <label htmlFor="topbar-case-search" className="sr-only">{t.searchLabel}</label>
          <input
            id="topbar-case-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="min-h-11 w-full bg-transparent text-sm text-ink outline-none placeholder:text-ink-subtle focus-visible:outline-none"
            placeholder={t.searchPlaceholder}
          />
        </form>
      ) : null}

      <div className="ml-auto flex min-w-0 items-center justify-end gap-2.5">
        <Button variant="ghost" icon={RefreshCw} onClick={() => window.location.reload()} title={t.refreshTitle}>
          {t.refresh}
        </Button>

        {publicSignup ? null : (
          <div className="hidden min-w-0 shrink overflow-hidden xl:block xl:max-w-[15rem] 2xl:max-w-[18rem]">
            <ActiveOrganizationSummary />
          </div>
        )}

        <LanguageToggle />

        <div className="min-w-0 max-w-72 rounded-card border border-brand-border bg-brand-soft px-4 py-1.5 text-sm">
          <p className="truncate text-sm font-semibold text-brand-strong">{user.name}</p>
          <p className="truncate text-xs text-ink-muted">{user.workspace}</p>
        </div>

        {user.showLogout ? (
          <Button variant="secondary" icon={LogOut} onClick={() => void user.logOut()} className="hidden shrink-0 2xl:inline-flex">
            {t.logOut}
          </Button>
        ) : null}
      </div>
    </header>
  );
}
