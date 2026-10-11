# PasaScope design language

Status: authoritative for the canonical therapist product in
`apps/pasascope-app/`.

PasaScope is a calm, friendly clinical workbench for therapist-reviewed
language-sample workflows. The visual direction, approved by the project owner
on 2026-10-12, is a light blue system: an ice-white canvas, white rounded cards,
a sky and azure brand family, soft blue-tinted elevation, pill actions, and one
obvious next step per screen. It keeps the structural discipline of a data
workbench: compact rows, clear selection, hairline separators.

## Product character

The interface is professional, approachable, lightweight, and trustworthy. Every
screen leads with its single next action. It must not resemble a generic
healthcare analytics dashboard, a marketing landing page, an AI sparkle
interface, or a Kanban clone, and decoration never competes with clinical
content: frosted glass is confined to navigation chrome and reading surfaces
stay opaque white.

The stable information architecture is Today, Cases, Session, Reports, and
Settings. Today is the focused workbench and is not a split view. Cases and
Session may use measured master-detail or editor-inspector layouts on tablet and
desktop. `/settings` remains canonical for both therapist settings and strictly
role-gated organization administration.

## Authoritative implementation

The executable design system has one source per responsibility:

- `apps/pasascope-app/src/design-system/tokens.css` — colors, spacing, radii,
  borders, shadows, type sizes, motion, layout dimensions, and z-index;
- `apps/pasascope-app/src/design-system/typography.css` — shared type hierarchy;
- `apps/pasascope-app/src/design-system/components.css` — reusable workbench
  panels, reading surfaces, controls, sticky bars, motion helpers, and the
  restrained transcript/wave ruler motif;
- `apps/pasascope-app/src/styles/globals.css` — imports, reset, body/app defaults,
  generic interaction timing, and global accessibility behavior only.

Feature code must consume semantic tokens. It must not redefine a second palette
or token vocabulary.

## Color

Colour follows a 60 / 30 / 10 split, and the palette contains no green, teal, or
turquoise anywhere, semantic states and data visualisation included.

- **60, canvas and surfaces:** ice-white canvas (`--color-page-bg`), true-white
  reading and working surfaces, pale blue hairlines.
- **30, sky family and navy ink:** sky tints for hero cards, icon tiles, step
  rails and graphics (`--color-sky*`); navy for text (`--color-text-*`) and for
  the audio waveform panel (`--color-navy`).
- **10, azure and coral:** azure (`--color-brand`) for the primary action,
  selection, active navigation and focus; coral (`--color-highlight`) as a
  small highlight.

Rules:

- One solid azure button per view. Other actions are secondary or ghost.
- Coral marks at most one thing per region (a count that needs attention, the
  child speaker, the logo). White body text on coral fails contrast, so a coral
  fill carries navy text or an icon, and coral text uses
  `--color-highlight-text`.
- Semantic state is never colour alone. Success is blue with a check icon,
  warning is amber, danger is a red distinct from coral, information is sky;
  each is paired with an icon or a label that names the state.
- Azure never floods a whole page; the hero card is the one large azure field
  a screen may have.

`src/__tests__/design-palette-contract.test.ts` enforces this: it rejects green
by hue, requires every `var()` to be defined, and checks WCAG AA for the allowed
text and fill pairings.

## Typography

Two faces, loaded through `next/font` and served from the app's own origin:

```css
/* reading: body, forms, tables, transcripts */
font-family: "Noto Sans Thai", "Noto Sans", system-ui, sans-serif;
/* display: h1–h3 and large numerals only */
font-family: "Prompt", "Noto Sans Thai", "Noto Sans", system-ui, sans-serif;
```

Prompt never sets body copy, form text, table cells, or transcript lines. Use
moderate weights and create hierarchy through scale and spacing. Page titles
are approximately 28–32px; section titles 20–24px; panel titles 16–18px; body
14–16px; transcript text 15–16px with generous line height; metadata 12–14px;
buttons 14–16px medium. Avoid marketing-scale display typography. Atkinson
Hyperlegible is permitted only in an explicit accessibility mode or a verified
Latin-only transcript context; it is not a competing global stack.

## Geometry and surfaces

- Controls (inputs, selects): 12px radius (`--radius-control`).
- Cards 20px, panels 24px, the outer shell 28px.
- Buttons, navigation items, status chips, and segmented controls are pills.
- Cards carry a soft blue-tinted shadow (`--shadow-soft`); stronger elevation is
  for the hero card, popovers, drawers, and modals.
- **Frosted glass** (`.glass-chrome`) is for chrome only: sidebar, top bar,
  mobile header, bottom navigation, and sticky action bars. Transcripts,
  findings, reports, tables, and forms sit on opaque white. The glass falls back
  to an opaque surface under `forced-colors`, `prefers-reduced-transparency`,
  and where `backdrop-filter` is unsupported.
- **Hero card** (`.hero-wave`): an azure field with two soft wave shapes, used
  once per screen at most to present the next action.
- Avoid nested card grids and gradients other than the hero card and the canvas
  wash.

## Shell and navigation

The product shell is quiet: a persistent left sidebar on desktop, a drawer plus
bottom navigation on mobile, and a thin top bar, all frosted. The shell never
competes with the surface it hosts.

- **Sidebar (desktop, ≥1024px):** brand (links to Today, the single home), one
  New Session action, and one list of destinations in canonical order: Today,
  Dashboard, Cases, Session, Reports, Settings. Destinations render at 44px hit
  height with an active-state fill and `aria-current="page"`.
- **Phone and tablet (<1024px):** a compact header with the menu button, brand,
  and the language toggle; the sidebar becomes a 264px drawer with backdrop.
  The open drawer traps focus, closes on Escape, and returns focus to the menu
  button; while closed it is hidden from the tab order and assistive
  technology. Below 768px a fixed bottom navigation shows exactly five labeled
  items (≤5-item rule) and content reserves its space.
- **Top bar (desktop):** case search (omitted on Cases, which has its own),
  refresh, organization summary, the language toggle, identity, and logout. It
  stays one line and never pushes content. It shows nothing that is not real:
  no placeholder notification count, no inert control.
- **Breadcrumbs:** deep flows (Cases → case → session step) use a quiet
  breadcrumb trail where ancestors link back and the current step is plain
  text. Breadcrumb links keep a 44px hit area via invisible padding.
- **Page headers:** a consistent `PageHeader` rhythm — optional eyebrow chip,
  one h1, a short description, optional meta chips, and one primary action
  group on the right.
- Every surface uses the same shell; navigation placement never changes by
  page type.

## Language

The interface is available in Thai and English, switched by the TH/EN toggle in
the top bar and the mobile header. Thai is the default for a first visit; the
choice is stored in the `pasascope_locale` cookie and read by the root layout,
so the first byte of every page is already in the chosen language and
`<html lang>` matches it.

- Strings live in per-feature catalogs (`*.messages.ts`, built with
  `defineMessages`) beside the feature that renders them. Both languages are
  required by the type, so a missing translation does not compile.
- Dates and numbers are formatted with `src/i18n/format.ts`.
- Clinical safety wording is single-sourced per language and follows
  `docs/ux/therapist-workflow/content-and-safety-language.md`.
- Unit tests and Playwright suites pin English; the language-switch coverage
  exercises Thai explicitly.

## Shared states

Loading, empty, and error states are humanized once and reused everywhere:

- **Loading:** shared `Skeleton` primitives (panels and lines) instead of
  spinner-only or bare-text loading; skeletons reserve space, pulse with
  `prefers-reduced-motion` respected, and expose `role="status" aria-live`.
- **Empty:** shared `EmptyState` with a title, one-sentence description, and a
  single next action when one exists.
- **Errors:** backend-unavailable banners with recovery copy; failed states
  state the cause and the recovery path.
- Disabled workflow actions always explain why inline (see the workflow-gates
  pattern) and link the reason with `aria-describedby`.

## Core screen contracts

### Today

Preserve the approved focused workbench: one backend-derived priority queue, one
next action per row, one prominent Start session action, status grouping inside
the queue, and a quiet contextual rail. Do not convert it to Kanban, analytics,
or case-management split view.

### Cases

Prioritize the question “Which case requires what action next?” Desktop and
tablet landscape use a compact list plus an authorized selected-case summary.
Default rows show case label, latest activity, workflow status, and one next
action. Mobile navigates from case list to a dedicated Case Detail route rather
than stacking list, analytics, progress, and activity.

### Session Transcript

Transcript lines remain directly editable. Selection is visually unmistakable
and exposed with `aria-selected`; focus is preserved when scrolling to a selected
line; secondary line actions live in an overflow menu.

- Desktop: editor remains at least 60% and normally about 65%; Audio/QA inspector
  is collapsible/resizable, does not clip, and never causes page overflow.
- iPad portrait: Transcript, Audio/QA, and context are switchable so the editor is
  never squeezed.
- Tablet landscape/1024+: use a measured approximately 65/35 split when space
  allows.
- Mobile: session context → sticky compact player → editable transcript →
  safe-area-aware sticky Save/QA controls. QA detail, report readiness, and
  technical provenance use progressive disclosure rather than permanent stacked
  panels.

### Session Intake

Intake is a guided flow of four steps — Details → Source material → Transcript
setup → Review & Start — shown one question at a time with a quiet step rail
rather than a dashboard of simultaneous forms. Consent verification gates the
flow before audio work. The source choice is explicit (Record in browser,
Upload audio, Upload .cha, Paste transcript); the pipeline progress bar narrows
to the stages that actually apply to the chosen path (paste/CHA never show
Upload or ASR). One primary action per step; disabled actions carry an inline
reason (see Shared states).

### Findings

Use three disclosure levels. Level 1 shows only clinical review groups: Language
sample, Lexical use, Interaction, Speech/intelligibility, and Data quality. Level
2 reveals feature details. Level 3 contains methods, reference evidence,
provenance, limitations, and interpretation cautions. No level makes a diagnosis
or normative conclusion.

### Reports

Reports is a calm library, not a feed: a status metric row, then three grouped
sections — Needs review, Needs regeneration, Signed reports — each with a
compact data table on desktop (Report, Updated, Version, Status, Action) that
collapses to a compact list on mobile. Each row carries exactly one action
(Review draft / Regenerate report / View signed report / Find session) that
opens the canonical Session Report workspace. Counts are workflow progress
only, never clinical outcome scores.

### Settings

Use category navigation and drill-down rather than an all-in-one card feed.
Therapist categories are Account, Organization, Accessibility & Display,
Notifications, Privacy & Security, Export, and Help. Authorized administrators
add Team, Invitations, Audit, Privacy Operations, and Integration Status.
Ordinary therapists do not see admin navigation, disabled admin controls, or
admin placeholders. Backend and server-boundary authorization remain mandatory.

## Motion

- Hover and selection: 80–120ms (`--motion-selection`, currently 120ms).
- Menus and popovers: 150–180ms (`--motion-popover`, currently 180ms).
- Drawers and inspectors: 180–240ms (`--motion-panel`, currently 220ms).
- Pane resize: immediate (`--motion-resize`, currently 0ms).

Use ease-out. `prefers-reduced-motion` makes motion effectively instant. Do not
decorate workflow data changes with animation.

## Accessibility

- WCAG 2.2 AA contrast and logical semantic structure.
- Visible focus; keyboard-complete transcript editing.
- `aria-selected` for selected lines.
- `aria-live` for save, job, and error results.
- Focus trap and trigger restoration for modal/drawer layers.
- Focus restoration after inspector, menu, or disclosure close where applicable.
- Essential states remain legible in forced-colors mode.
- Input errors are associated through `aria-describedby`.
- Shortcuts do not override browser defaults.
- Touch layouts preserve 44px hit areas without inflating desktop controls.
- Sticky controls reserve content space, respect safe-area insets, and do not
  overlap content at native size or 200% zoom.

## Clinical and authorization boundaries

Safety and authorization are behavior, not decoration. The persistent product
boundary may be concise—“Decision-support only · Therapist review required”—but
strong contextual warnings remain at Findings interpretation, AI-assisted
review, report generation, and export/sign-off. Reducing repeated copy must never
remove consent, stale-state, report-safety, provenance, or role gates.

Hiding controls is never authorization. Admin data reads and mutations remain
backend and server-boundary authorized. Transcript edits invalidate existing
downstream Findings and editable Report drafts server-side; stale Findings are
not current and stale Reports cannot be signed or exported.

## Anti-patterns

- Any green, teal, or turquoise, including for success states and charts.
- White body text on coral, or coral used as a button fill.
- More than one solid azure button in a view.
- Frosted glass on a reading surface, or blur that lowers text contrast.
- Raw Tailwind palette classes (`slate-*`, `indigo-*`, …) or `dark:` variants;
  the product is light-only and every colour comes from a token.
- Sparkles, floating action clutter, and marketing blocks.
- Placeholder controls or invented values on a real screen.
- Repeating the same long safety paragraph in simultaneous panels.
- Exposing every Findings method/reference paragraph by default.
- Squeezing the tablet transcript beside an always-open inspector.
- Showing sample or fallback records as backend-confirmed success.
- Adding visual layout or feature rendering to the identity-scoped Session
  orchestration controller.

## Evidence contract

Pure visual work is proven through approved-concept comparison, responsive
screenshots at 390×844, 768×1024, 1024×1366, 1280×800, and 1440×900,
accessibility checks, and a fidelity ledger. Behavior changes require
characterization or failing regression tests first. Final verification includes
lint, typecheck, unit tests, production build/bundle budgets, real-contract and
explicit-demo Playwright, responsive/accessibility suites, role/route contracts,
and the 100/500/1,000-line transcript benchmark.
