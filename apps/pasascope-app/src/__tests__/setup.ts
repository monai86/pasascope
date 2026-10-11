import "@testing-library/jest-dom/vitest";
import { render, type RenderResult } from "@testing-library/react";
import { beforeEach, vi } from "vitest";

import { setLocaleWithoutProviderForTests } from "@/i18n/locale-provider";
import { resetApiRuntimeSettingsCacheForTests } from "@/lib/api";

// The suites assert English copy. Thai is the product default, so the language
// is pinned here; a test that needs Thai renders through renderWithLocale.
setLocaleWithoutProviderForTests("en");

export const routerPush = vi.fn();
export const routerReplace = vi.fn();
export const routerRefresh = vi.fn();
export const redirectMock = vi.fn((href: string): never => {
  const error = new Error("NEXT_REDIRECT");
  Object.assign(error, { digest: `NEXT_REDIRECT;replace;${href};307;` });
  throw error;
});

type AsyncPage<TProps = any> = (props: TProps) => React.ReactNode | Promise<React.ReactNode>;

export async function renderAsyncPage(
  page: AsyncPage,
  props?: unknown,
) {
  const content = await page((props ?? {}) as any);
  return render(content);
}

if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    fillText: vi.fn(),
    strokeRect: vi.fn(),
    setLineDash: vi.fn(),
  }) as any;
}

beforeEach(() => {
  resetApiRuntimeSettingsCacheForTests();
  routerPush.mockReset();
  routerReplace.mockReset();
  routerRefresh.mockReset();
});

// Server components read the language from the request cookie, which does not
// exist outside a request.
vi.mock("@/i18n/server", () => ({
  getRequestLocale: async () => "en",
  getMessages: async <T,>(catalog: { en: T }) => catalog.en,
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
  useRouter: () => ({
    push: routerPush,
    replace: routerReplace,
    prefetch: vi.fn(),
    refresh: routerRefresh,
  })
}));
