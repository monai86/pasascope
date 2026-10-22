# Known Limitations

Numbers below come from `reports/metrics/EVALUATION_SUMMARY.md`.

- **Decision support only, not diagnostic.** PasaScope is a research and
  education prototype. It does not diagnose ASD, gives no risk score, and
  applies no Thai norms or cutoffs because none are verified.
- **Transcription is a draft.** On adult read Thai (30 FLEURS clips) the
  character error rate is 6.5% in accurate mode and 19.2% in fast mode. On real
  recordings of children, uncorrected, the word error rate is 29–36% for
  English preschoolers and about 86% for Thai toddlers under two. No Thai
  preschool recordings with gold transcripts were available. The program
  computes no measure until the therapist has corrected and attested the
  transcript.
- **Child/adult labels can be wrong.** On 16 English recordings of children
  aged 2;6–5;6, 87.0% of utterances got the right speaker (child F1 0.81).
  Separation fails more often when speakers sound alike or talk over each
  other. A clinic-trained model does better (94–97%) but needs at least four
  attested sessions from two children.
- **Utterance boundaries follow simple rules.** Thai drafts start a new
  utterance at a pause of 0.6 s or more; English drafts use a small logistic
  regression model. A child who hesitates mid-sentence can get two utterances,
  which lowers MLU until the therapist merges them.
- **Echolalia and pronoun cues are heuristics.** In 40 scripted Thai turn pairs
  the echolalia rule caught all 20 echoes and also flagged 4 of 20 ordinary
  answers (precision 83%). Only immediate echoes are detected. Thai pronoun
  cues cover second-person pronouns followed by a desire or state verb only.
  Cues never change a measure or a report by themselves.
- **Measures are checked against CLAN on English only.** On 1,961 TalkBank
  transcripts MLU-w, NDW-100, MATTR-50 and VOCD-D agree with CLAN (ICC ≥ 0.9997).
  There is no reference tool for Thai; the Thai path uses the same counting
  code after PyThaiNLP word segmentation.
- **Turn-taking reference values are English.** They come from TalkBank toy-play
  transcripts and are not Thai norms.
- **CHAT support is a subset.** Import and export cover headers, speaker tiers,
  timestamps and the codes the program uses; other tiers are skipped with a
  warning. Full CLAN compatibility is not validated.
- **Runtime and reference features differ.** Runtime language-sample features
  are not computed the same way as the earlier reference cohorts: on one sample
  the runtime reports MLU-words 2.0 and unintelligible ratio 0.1667, the
  reference extractor 3.0 and 0.25 (`apps/api/tests/test_reference_runtime_parity.py`).
  Reference evidence stays disabled until a clinician chooses one definition
  and both sides use it.
- **Earlier ML work is not clinical validation.** The Gate 1 result is an
  engineering check on proxy labels from public English corpora. No model
  output is shown to therapists.
- **One computer, one user.** Records stay in a local SQLite database and audio
  folder. There is no multi-user access, server sync or remote backup beyond the
  program's own backup file.
- **Usability is untested.** No therapist has used the program in a timed
  session yet (`docs/PILOT_USABILITY_PROTOCOL.md`).
