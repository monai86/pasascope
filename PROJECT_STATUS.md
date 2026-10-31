# Project Status

Current maintained version: `v1.8.2`.

PasaScope is a research prototype that helps a speech-language therapist turn a
recording or transcript of a child's speech into a reviewed transcript,
descriptive language-sample measures, review cues and a signed session report.
It is not a diagnostic device and has not been clinically validated for Thai
children.

## Deliverable

- **Desktop program** (`packages/desktop/`): the term paper's main deliverable.
  Released as v1.8.2 for macOS (`.dmg`) and Windows (installer), with in-app
  updates from GitHub Releases. One computer, SQLite, no server.
- **Shared service layer** (`apps/api/app/services`): consent checks, measures,
  review cues, report drafting, report safety check and audit events, called
  in-process by the desktop program.
- **Evaluation** (`reports/metrics/`, summary in `EVALUATION_SUMMARY.md`):
  agreement with CLAN on 1,961 transcripts, Thai ASR accuracy, child/adult
  speaker attribution, echolalia cue check, turn-taking reference values.
- The paused web app, the Tkinter GUI, the TUI and the legacy research API were
  removed from the working tree on 2026-10-23 (git tag `web-app-final`).

## Open items

- No recordings of Thai children aged 2;6–7 years have been evaluated yet.
- The therapist usability test has not been run; the protocol is ready
  (`docs/PILOT_USABILITY_PROTOCOL.md`).
- No real transcript review-time data yet
  (`scripts/report_transcript_review_time.py --desktop`).

## Limitations

See [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md). In short: no diagnosis,
no verified Thai norms or cutoffs, ASR drafts must be corrected by the
therapist, and Gate 1 of the earlier ML work is an engineering check on public
English corpora, not clinical validation.

See `docs/PROJECT_SOURCE_OF_TRUTH.md` for the rules every change must follow.
