# PasaScope product design contract

This document defines the current UI contract for the canonical therapist product in `apps/pasascope-app`. Root `DESIGN.md` is the human-readable product authority. The executable source is split by responsibility under `src/design-system/`: `tokens.css` owns every semantic token, `typography.css` owns the shared type hierarchy, and `components.css` owns reusable workbench primitives. `src/styles/globals.css` imports those files and is limited to reset, body/app defaults, generic transition binding, and global accessibility rules. Historical concepts and screenshots are evidence, not competing design systems.

## Product character

PasaScope is a calm clinical workbench for therapist-reviewed language-sample workflows. It must feel precise, quiet, readable, and trustworthy without implying automated diagnosis or Thai clinical validation. Use clear hierarchy, restrained surfaces, explicit workflow state, and one obvious next action.

## Typography

The unified Thai–Latin reading stack is:

```css
font-family: "Noto Sans Thai", "Noto Sans", system-ui, sans-serif;
```

This stack is mandatory for the product shell, controls, forms, tables, reports, and mixed-script transcript content. Prompt is the display face for h1–h3 and large numerals only (`font-display`). Both load through `next/font` in `src/app/fonts.ts` and are served from the app's origin. Do not introduce Inter, Haas, or Atkinson Hyperlegible as a competing global stack. Atkinson Hyperlegible may be offered only through a deliberate accessibility preference or in a Latin-only transcript context where mixed-script metric changes cannot occur.

## Layout contracts

- Today uses a focused workbench: one prioritized queue, one next action per row, one prominent Start session action, and a quiet contextual rail. Status grouping belongs inside the queue, not in a full Kanban board.
- Cases and Session Workspace may use split views on tablet and desktop. Today must not.
- Session Workspace uses validated `?view=intake|transcript|findings|report`; missing or invalid values resolve to `intake`.
- `/settings` is canonical. Organization administration exists only in role-gated sections within Settings.
- Desktop transcript editing remains dominant at 60% width or more. The QA inspector is collapsible or resizable and may not clip.
- On iPad portrait, Audio/QA can collapse or switch views so the transcript remains usable.
- On mobile, sticky media and action regions honor safe-area insets and reserve content space.

## Shell, navigation, and shared states

- The shell is a quiet frosted frame: a 264px sidebar on desktop (brand linking to Today, New Session, and one destination list in canonical order at 44px hit height), a compact header with the menu button and language toggle below 1024px, a focus-trapping drawer, a bottom navigation of exactly five labeled items below 768px, and a one-line desktop top bar (case search, organization, language, identity). Every surface uses the same shell; `AppShell` owns the frame and gates. Shell strings live in `src/components/shell.messages.ts`.
- Deep flows render a breadcrumb trail (Cases → case → session step) with 44px hit areas via invisible padding; the current step is plain text.
- Page headers follow one `PageHeader` rhythm: optional eyebrow chip, one h1, short description, optional meta chips, one action group.
- Session Intake is a guided flow: Details → Source material → Transcript setup → Review & Start, one question at a time with a quiet step rail. The pipeline progress bar (`PipelineProgressBar`) reflects the chosen source path — paste/CHA paths omit Upload and ASR stages entirely.
- Reports is a calm library: a status metric row, then grouped sections (Needs review, Needs regeneration, Signed reports) rendered as a compact `DataTable` on desktop and a compact list on mobile, with one action per row into the canonical Report workspace.
- Shared states: `Skeleton`/`SkeletonPanel` for loading (space-reserving, reduced-motion aware, `role="status"`), `EmptyState` with a next action, backend-unavailable banners with recovery copy, and inline blocked-reasons on disabled workflow actions wired with `aria-describedby` (the workflow-gates pattern).

### Chat shell (behind `NEXT_PUBLIC_CHAT_SHELL`)

`AppShell` still owns the frame and the gates; it renders `ChatShellFrame` (`src/components/chat-shell/`) when `isChatShellFlagOn()` and the confirmed runtime settings report public sign-up with open review gates. Every other configuration renders the workbench shell above, so the two never mix on one deployment.

- `ChatShellFrame` lays out `ChatNav`, the page and the side panel, and owns the drawer and sheet (focus trap, Escape, focus return). `ChatShellPanel` and `ChatShellHeader` are how a page fills the side panel and the phone/tablet header; outside the chat shell they render nothing.
- Destinations come from `CHAT_NAVIGATION` in `src/services/navigation/workbench-navigation.ts`; `src/__tests__/chat-shell.test.tsx` asserts the ordered list.
- Conversation building blocks live in `chat-primitives.tsx` (`ChatThread`, `UserBubble`, `AssistantMessage`, `ChatCard`, `QuickReply`, `ChatComposerDock`) and `chat-composer.tsx`. Build conversation screens from these.
- `/` and `/today` both render `WorkQueueDashboard`, which shows the chat home (`src/features/chat-home/`) in the chat shell and the Today queue otherwise. The chat home reads `GET /dashboard/summary` and the case list; starting a session runs `StartSessionThread`, which grants consent before it creates the session.
- A session's conversation is the `chat` view of the same Session controller. `chat-thread-model.ts` is a pure function from session facts to thread items and replies; it carries no display text, and `chat.messages.ts` supplies the words. Rules that must hold are tested there: no audio while consent is inactive, no "set the rest" when no line has a speaker, no measures without a child line, stale measures never shown, a blank instead of a number the backend did not send.
- `?view=chat` is a route view, not a workflow step: `sessionViews` stays the four steps, and `SessionRouteView` adds `chat`. In the chat shell `?view=intake` also opens the conversation; without it `?view=chat` falls back to Intake.

## Surfaces and controls

Use the semantic color, radius, and surface tokens in `src/design-system/tokens.css`, through the Tailwind aliases in `tailwind.config.ts` (`bg-surface`, `text-ink`, `border-line`, `bg-brand`, `rounded-card`, …); do not redefine them in feature styles and do not use raw Tailwind palette classes or `dark:` variants. Build screens from the primitives in `src/components/ui/` (Button, IconButton, Card, Badge, Field, Input, Select, Textarea, SegmentedControl, StatTile, Stepper, Dialog, ConfirmDialog, EmptyState, ErrorState, Tabs) before writing new markup. Reading surfaces are true white with pale blue hairlines; controls use a 12px radius, cards 20px, panels 24px; buttons and chips are pills. Frosted glass (`.glass-chrome`) is for navigation chrome and sticky action bars only. Colour follows the 60 / 30 / 10 rules in the root `DESIGN.md`, enforced by `src/__tests__/design-palette-contract.test.ts`. Controls may be visually compact on desktop, but touch devices require a 44px interactive hit area. Transcript lines remain directly editable; selected lines are unmistakable and use `aria-selected`. Secondary line actions belong in an overflow menu.

## Motion

Use the timing tokens in `src/design-system/tokens.css`:

- selection and hover: `--motion-selection` (120ms; acceptable range 80–120ms)
- popovers and menus: `--motion-popover` (180ms; acceptable range 150–180ms)
- drawers and panels: `--motion-panel` (220ms; acceptable range 180–240ms)
- pane resizing: `--motion-resize` (immediate)

Respect `prefers-reduced-motion`. Never animate pane resizing in a way that delays direct manipulation.

## Accessibility acceptance

- Transcript selection exposes `aria-selected`.
- Save, job, and error results use an appropriate `aria-live` region.
- Modal and drawer focus is trapped and restored to the trigger on close.
- Essential states remain legible in `forced-colors` mode.
- Input errors are linked to their fields with `aria-describedby`.
- Keyboard shortcuts do not override browser defaults and are documented where exposed.
- Scrolling to a selected transcript line preserves keyboard focus.
- Focus indicators remain visible and touch targets remain at least 44px on touch devices.

## Authorization and safety

Hiding controls is never an authorization boundary. Admin routes, data reads, and mutations must be backend- and server-boundary authorized. Therapists receive only the minimum read-only care-team summary already present on an authorized case record. Role, invitation, privacy, care-team, and organization-management mutations retain backend audit logging.

## Session architecture

The canonical Session boundary is deliberately layered:

- `session-workspace.tsx` resolves the canonical view and isolates Report as its own lazy feature.
- `useSessionWorkspace` in `session-workspace-model.tsx` is the identity-scoped controller. It owns request sequencing, cancellation guards, persistence, and workflow mutations.
- `session-workspace-view.tsx` is the typed presentational dispatcher and lazy-loads Intake, Transcript, and Findings independently.
- Intake mutations enter through the Session controller; Intake steps and source/result presentation are split from the route-level view.
- Report transport lives behind `session-report-service.ts`, identity-scoped orchestration lives in `use-session-report.ts`, and the Report view remains presentational.
- Analysis transport lives behind `services/adapters/analysis-adapter.ts`: model-informed decision support and evidence review (ML readiness, ML decision support, cues acknowledgement, profile evidence disposition) **and feature extraction** (session features read, feature-definition catalog, `runBackendAnalysis` extraction POST → summarized via the `summarizeAnalysis` domain helper in `lib/workflow.ts`). The Session controller imports from that adapter, and `lib/workflow.ts` only re-exports it for backward compatibility.
- Findings derivations and small provenance/status components live in `session-findings-support.tsx` so the Findings screen stays within the complex-container budget.
- The transcript editor separates controller state, the directly editable memoized line list, and pure/support calculations into `transcript-editor-panel.tsx`, `transcript-line-list.tsx`, and `transcript-editor-support.tsx`.
- Each feature view owns only its cohesive screen layout and interaction presentation; reusable transport operations live behind services and workflow adapters.

The controller is intentionally kept as one identity-scoped orchestration boundary so a late request or mutation cannot settle into a different Session. It must not absorb feature layout. New transport behavior should first be added to the service/adapter boundary, and new view behavior belongs in the relevant feature view.

## Settings architecture

`/settings` remains the single route. Desktop uses a category rail and mobile uses category selection/drill-down. Shared categories are Account, Organization, Accessibility & Display, Notifications, Privacy & Security, Export, and Help. Team, Invitations, Audit, Privacy Operations, and Integration Status are organization-admin only. `settings-workspace.tsx` owns the role-gated section switch and organization-admin lifecycle controller; navigation, therapist presentation, backend-authorized care-team administration, and reusable status/lifecycle presentation are split into dedicated components. Moving those components does not weaken the server route or backend authorization boundary: ordinary therapists never mount admin controllers, receive admin navigation, or fetch admin lifecycle data. Failed or malformed admin responses clear lifecycle state and never substitute sample records.

Complex feature containers are limited to 500 lines by an architecture test. The identity-scoped Session controller is the documented exception because splitting its request identity and stale-settlement coordination would weaken the race-safety boundary; it contains no feature layout.

## Today architecture

The canonical Today route is a backend-driven feature boundary:

- `WorkQueueDashboard` is a thin authenticated-shell entry point; its data controller mounts only after the shell access gate allows workspace content.
- `useTodayWorkbench` owns request identity, cancellation, retry, and remote-state translation.
- `today-workbench-adapter.ts` loads authorized Cases and Reports in parallel and rejects malformed non-array payloads rather than rendering an inferred success state.
- `today-workbench-model.ts` deterministically derives one operational next action per case and groups those items inside the queue.
- `TodayWorkbenchView` and `TodayContextRail` are presentational and do not call APIs.

Today never imports product rows from `mock-data`. Sample records remain isolated to explicitly flagged `/demo/*` surfaces.

## Verification

Visual changes require approved-concept comparison, responsive screenshots at the required viewports, accessibility checks, and recorded intentional deviations. Behavior changes require characterization or failing regression tests first. Frontend contract types must remain aligned with backend schemas.
