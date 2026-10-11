# Known Limitations

- **Decision-support only, not diagnostic**: This is a research and education prototype, not a clinical diagnostic product or validated clinical tool. It does not provide automated diagnoses.
- **ASR is experimental**: Browser recording and automated speech recognition (ASR) are experimental. Uploaded recordings are transcribed by on-device Whisper only when `LINGUALENS_ASR_LOCAL_WHISPER_ENABLED=true`; otherwise transcription is unavailable and the therapist pastes or imports the transcript. The synthetic mock provider is never selected by the web app.
- **Whisper is not trained for young children's Thai**: expect wrong words, merged turns, and wrong speaker labels, especially with quiet, overlapping, or unclear speech. Speaker separation relies on voice differences and fails when speakers sound alike. Measured so far (see `reports/metrics/`): on 30 FLEURS Thai clips of adults reading formal sentences the mean character error rate is 29% with the `small` model and 20% with `medium`; on six scripted text-to-speech therapy-style dialogues it is 6.7% and 0.8%. No Thai child speech has been tested, and child/adult separation has not been evaluated for Thai.
- **Echolalia and pronoun cues are heuristics**: a natural answer that reuses the adult's words can be flagged as an echo (4 of 20 ordinary replies in the scripted check, with all 20 scripted echoes caught), and only immediate echoes are detected.
- **Feature values are not CLAN values**: on 1,961 TalkBank transcripts the app's child word count tracks CLAN closely (r = 0.997, median difference 4.7%), but it counts about 21% more distinct words and more utterances. Do not compare app values with CLAN-based published norms. Thai pronoun cues cover second-person pronouns followed by a desire or state verb only.
- **Desktop GUI radar chart is not a normative comparison**: it plots one session's measured values on fixed drawing scales. It does not compare the child with other children, because no verified Thai norm exists.
- **Basic CHAT import/export only**: Import and export support basic CHAT file structure (metadata headers, speaker tiers, timestamps) and skip unsupported tiers with warnings.
- **Not full TalkBank/CLAN-grade compatibility yet**: The parser does not validate full TalkBank/CLAN compatibility or enforce all syntactic conventions of the CLAN utility suite.
- Audio remains memory-only in the browser and is lost on page refresh.
- Current-tab browser persistence is for demonstrations only and must not contain real identifiers, sensitive clinical data, or raw transcript recordings.
- Feature extraction provides descriptive language-sample cues for clinical interpretation, not diagnostics.
- ML output is editable/dismissible decision support trained on limited/public datasets and is not clinically validated.
- Reports require therapist review. Local finalization is not a production signature or secure caregiver-delivery workflow.
- Markdown and HTML export are available. PDF export is not yet implemented.
- Runtime language-sample features are not computed the same way as the reference cohorts they would be compared with: on one sample the runtime reports MLU-words 2.0 and unintelligible ratio 0.1667, the reference extractor 3.0 and 0.25 (`apps/api/tests/test_reference_runtime_parity.py`). Reference evidence must stay disabled until a clinician chooses one definition and both sides use it.
- The SQL repository keeps a per-process cache of clinical records and writes legacy paths as a whole-snapshot upsert. It must run as a single API worker (`WEB_CONCURRENCY=1`, enforced at startup); a second instance would read and write stale state. Per-request queries need a separate ADR.
- Production authentication, encrypted private storage, durable queues, deployment monitoring, and audited role enforcement remain future work.

For deeper engineering detail, see the archived v2 known-limitations document in
`docs/`.
