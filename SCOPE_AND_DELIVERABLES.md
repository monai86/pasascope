# Scope and Deliverables

Term paper: "การประยุกต์ใช้ปัญญาประดิษฐ์เพื่อสนับสนุนการประเมินทางคลินิกสำหรับเด็กออทิสติก
(AI-Assisted Program for Clinical Assessment of Autism)".

## Primary Deliverable

The desktop app (`packages/desktop`, started with `./run_gui.sh` or the
`pasascope` command) is the primary deliverable. It is one program on the
therapist's computer: no server, recordings and records stay on that machine
(a SQLite database and an audio folder in the user's application-data
folder), and every change is written to an audit log.

It demonstrates one human-reviewed workflow per session:

1. Open a case and record the caregiver's consent (no session or recording
   before consent is recorded)
2. Add a session
3. Record from the microphone or import a recording; on-device Whisper drafts
   a transcript with child/adult speaker labels (or import an existing CHAT or
   plain-text transcript)
4. The therapist corrects the draft against the waveform, utterance by
   utterance, and attests it
5. Language-sample features and review cues are computed from the attested
   transcript; the therapist confirms or dismisses each cue, with the
   adult/child utterance pairs behind an echolalia cue shown in context
6. A Thai session report is drafted, edited, signed, and exported (PDF, HTML,
   Markdown; the transcript as CHAT)

The AI contribution is the draft transcript with child/adult speaker
separation and the transcript-derived features and review cues. Every
automated output is a draft that the therapist reviews before it is used.

The desktop app runs the same service layer as the API (`apps/api/app/services`)
in its own process, so consent checks, feature extraction, review cues,
report drafting, the report safety check and the audit events are one
implementation.

## Supporting Deliverable

The therapist web app (`apps/pasascope-app` + `apps/api`, `/api/v1`) is the
earlier multi-user version of the same workflow. Its development is paused;
it shares the service layer above and is not part of the presented system or
its evaluation.

## Research Output

- `reports/metrics/feature_agreement_clan.*`: the app's language-sample
  measures against CLAN on 1,961 TalkBank transcripts.
- `reports/metrics/thai_asr_public.*`: Thai recognition accuracy by model size
  on public adult read speech (FLEURS).
- `reports/metrics/thai_asr_evaluation*.*`: draft-versus-gold accuracy on
  scripted Thai dialogues (`scripts/evaluate_thai_asr.py`), for the
  multilingual and the Thai fine-tuned model.
- `reports/metrics/asr_desktop_tuning.md`: making on-device transcription fast
  enough on a therapist's laptop, the accuracy/speed choice between the two
  models, and the faults found on the way.
- `reports/metrics/echolalia_cue_check.md`: the Thai echolalia rule against 40
  labelled turn pairs.
- `reports/metrics/transcript_review_time.csv`: time from draft to attestation
  (`scripts/report_transcript_review_time.py --desktop`).
- `reports/ml/`: the classifier study on public English corpora. It separates
  groups within one corpus but not across corpora, and site, task and age
  explain most of the pooled accuracy. This is the reason the product is
  decision support with review cues, not a classifier. No model output is shown
  to therapists.

## Clinical Boundary

This is a clinical decision-support prototype and research demonstration. It is
not a deployed clinical system, not a diagnostic device, and not clinically
validated for Thai children. It does not diagnose ASD, and it applies no Thai
norms or cutoffs because none are verified.

## Out of Scope for the Term Paper

These exist in the repository as groundwork and are not part of the presented
system or its evaluation:

- The web app and its production deployment: multi-tenant isolation, Supabase
  Auth/MFA, RLS, managed storage, invitation and break-glass flows, staging
  evidence scripts.
- The earlier Tkinter desktop GUI (`packages/gui`, `./run_gui.sh --legacy`).
- The Assessment v2 workflow (removed).
- The terminal TUI.
- Clinical diagnosis, risk scores, and Thai clinical validation claims.
