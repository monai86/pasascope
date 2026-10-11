# Scope and Deliverables

Term paper: "การประยุกต์ใช้ปัญญาประดิษฐ์เพื่อสนับสนุนการประเมินทางคลินิกสำหรับเด็กออทิสติก
(AI-Assisted Program for Clinical Assessment of Autism)".

## Primary Deliverable

The therapist web app (`apps/lingualens-app` + `apps/api`, `/api/v1`) is the
primary deliverable. It demonstrates one human-reviewed workflow:

1. Open case and record consent
2. Add session
3. Record or upload audio; on-device Whisper produces a draft transcript
4. Therapist corrects and attests the transcript
5. Extract language-sample features and review cues
6. Generate, sign off, and export the Progress Report

The AI contribution is the draft transcript with child/adult speaker
separation and the transcript-derived features and review cues. Every
automated output is a draft that the therapist reviews before it is used.

## Supporting Deliverable

The desktop GUI (`packages/gui`, `./run_gui.sh --mock`) is an offline research
tool. It runs the same audio pipeline and Thai language-sample analysis on one
machine with no server, for settings where recordings must not leave the
device. It is not a second product.

## Research Output

- `reports/metrics/thai_asr_evaluation.*`: draft-versus-gold transcript
  accuracy and feature drift on local Thai recordings
  (`scripts/evaluate_thai_asr.py`).
- `reports/metrics/transcript_review_time.csv`: time from draft to attestation
  (`scripts/report_transcript_review_time.py`).
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

- Production deployment: multi-tenant isolation, Supabase Auth/MFA, RLS,
  managed storage, invitation and break-glass flows, staging evidence scripts.
- The Assessment v2 workflow (`/api/v2`, `/assessments/...`).
- The terminal TUI.
- Clinical diagnosis, risk scores, and Thai clinical validation claims.
