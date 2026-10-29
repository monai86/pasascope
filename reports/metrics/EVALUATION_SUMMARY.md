# PasaScope Evaluation Summary

What has been measured about the desktop app, with the numbers for the term paper and links to the full reports. Version: 1.7.5 (feature schema `features-basic-v3`). Each section names the script that reproduces it.

| Question | Data | Headline | Report |
|---|---|---|---|
| Does the app compute the measures the way CLAN does? | 1,961 English TalkBank child transcripts | MLU-w, NDW-100, MATTR-50 and VOCD-D: ICC(A,1) ≥ 0.9997; 94–96% identical values | [`core_measures_clan.md`](./core_measures_clan.md) |
| How accurate is Thai transcription? | 30 FLEURS Thai clips, adult read speech | Character error rate 6.5% in accurate mode, 19.2% in fast mode | [`thai_asr_public.md`](./thai_asr_public.md) |
| ...on Thai speech the model never saw? | 150 LOTUSDIS utterances, adult conversation | Character error rate 18.3% (accurate, near microphone), 25.2% at 2 m | [`thai_asr_lotusdis.md`](./thai_asr_lotusdis.md) |
| Does it tell the child from the adults? | 16 recordings of children aged 2;6–5;6 | 87.0% of utterances right; child F1 0.81 | [`speaker_attribution_real_children.md`](./speaker_attribution_real_children.md) |
| How far is an uncorrected draft from the truth? | Real child recordings, English and Thai | Usable as a draft from about 2;6 in English; not for Thai toddlers | [`end_to_end_summary.md`](./end_to_end_summary.md) |
| Does the echolalia cue find echoes? | 40 scripted Thai adult/child turn pairs | Recall 100%, precision 83% | [`echolalia_cue_check.md`](./echolalia_cue_check.md) |
| What do the turn-taking measures look like? | 1,120 toy-play transcripts (TD, LT, ASD) | Reference values by age and group | [`turn_taking_reference.md`](./turn_taking_reference.md) |
| Can therapists use it, and does it save time? | Not run yet | Protocols ready | [`docs/PILOT_USABILITY_PROTOCOL.md`](../../docs/PILOT_USABILITY_PROTOCOL.md), [`docs/TIMING_PILOT_PROTOCOL_TH.md`](../../docs/TIMING_PILOT_PROTOCOL_TH.md) |

## 1. Measures agree with CLAN

CLAN is the reference tool for CHAT transcripts. UnixCLAN (`kideval`, and `freq +b50` for MATTR) and the app's feature provider were run on the same 1,961 transcripts from 13 TalkBank corpora (TD 980, LT 408, NH 170, HL 138, ASD 136, SLI 113, DD 16).

| Measure | n | Same value as CLAN | ICC(A,1) | 95% limits of agreement (app − CLAN) |
|---|---|---|---|---|
| MLU-w | 1,960 | 94.9% | 1.0000 | −0.002 to +0.002 words |
| MLU50-w | 1,713 | 98.4% | 1.0000 | −0.031 to +0.028 words |
| NDW-100 | 1,688 | 96.3% | 0.9997 | −0.41 to +0.36 words |
| MATTR-50 | 1,755 | 94.0% | 0.9999 | −0.003 to +0.002 |
| VOCD-D | 1,755 | (random sampling) | 0.9997 | −0.83 to +0.80 |
| Different words | 1,961 | 85.5% | 1.0000 | −2.1 to +1.7 words |

Where the values differ, they differ by a word or two per transcript (the limits of agreement above). Within the ASD transcripts alone (n = 136) every ICC is at least 0.998. The comparison is on English, because CLAN has no Thai word segmentation; the Thai path shares the same counting code after PyThaiNLP splits the words. Script: `scripts/evaluate_core_measures_clan.py`.

## 2. Thai transcription

On the first 30 clips of the FLEURS Thai test set (5.4 minutes of adults reading sentences), transcribed afresh with the app's current code:

| App mode | Model | Character error rate (mean) | Clips under 10% CER | Time / audio length |
|---|---|---|---|---|
| Accurate (default) | Thonburian Whisper medium, fine-tuned for Thai | **6.5%** | 80% | 3.0 |
| Fast | Whisper medium, multilingual | 19.2% | 17% | 0.8 |
| (not used) | Whisper small, multilingual | 27.1% | 3% | 0.5 |

This is read adult speech in quiet conditions: the best case. Children's play is harder (section 4). Script: `scripts/evaluate_thai_asr_public.py`.

The Thai model was fine-tuned on data that include FLEURS, so the figures above may be optimistic. LOTUSDIS (NECTEC, 2025) was released after the model's last update: 150 single-speaker utterances of unscripted three-person Thai conversation, recorded at once by a microphone near the speaker and a device 2 m away.

| App mode | Microphone | Character error rate (mean) | Thai-script utterances only |
|---|---|---|---|
| Accurate (default) | near (12–15 cm) | **18.3%** | 13.6% |
| Accurate (default) | 2 m | 25.2% | 20.4% |
| Fast | near | 28.8% | 24.7% |
| Fast | 2 m | 32.6% | 28.1% |

Casual conversation roughly triples the error rate of read speech, and the accurate mode stays well ahead of the fast mode. "Thai-script utterances" leaves out the 39 utterances where the corpus writes English loanwords in Latin letters, which the models write in Thai. The fast mode returned nothing for 11 of the 150 short clips (the hallucination filter judged them silence); the accurate mode for 1. Script: `scripts/evaluate_thai_asr_lotusdis.py`.

## 3. Child or adult

Every measure is computed from the child's utterances, so a speaker mistake moves MLU and NDW as much as a transcription mistake. On 16 EllisWeismer recordings (8 typical, 8 late talkers, 2;6–5;6; 2,838 utterances), with the utterance boundaries taken from the corpus:

| Method | Utterances right | Child F1 | Median MLU-w shift |
|---|---|---|---|
| Pitch only | 59.7% | 0.58 | 0.44 words |
| **App default: child/adult frame model + speaker clusters** | **87.0%** | **0.81** | **0.22 words** |

Trained on a clinic's own attested sessions, the model reaches 94–97% for children under 7 in the same setting (`clinic_speaker_model.md`). Scripts: `scripts/evaluate_speaker_attribution.py`, `scripts/evaluate_clinic_speaker_model.py`.

## 4. From recording to measures, uncorrected

The whole pipeline on real recordings, nothing corrected by hand, against the corpus transcripts:

| | EllisWeismer (English, 2;6–5;6) | ENNI (English, under 7) | CRSLP (Thai, 1;9–2;0) |
|---|---|---|---|
| Word error rate, all speakers | 36.4% | 29.0% | 85.7% |
| Child MLU-w, mean distance from gold | 0.59 words | 1.69 words | 1.32 words |
| Child MLU-w, correlation with gold | 0.94 | −0.36 | 0.65 |

For preschool English the uncorrected child MLU already ranks children almost as the gold does, and keeps the late-talker effect size (Cohen's d −0.69 against −0.68). For Thai toddlers under two most of the speech is not transcribed correctly (CER 75%). This is why the app will not compute any measure until the therapist has corrected and attested the transcript. Script: `scripts/evaluate_end_to_end.py`.

## 5. Echolalia cue

On 40 scripted Thai adult/child turn pairs labelled by hand, the rule flagged all 20 echoes (recall 100%) and 4 of 20 ordinary answers that reuse the adult's words (precision 83%). Cues are shown for the therapist to confirm or dismiss; they never change a measure or a report by themselves. Script: `scripts/evaluate_echolalia_cue.py`.

## 6. Turn-taking reference values

Child response rate and the related measures on 1,120 TalkBank toy-play transcripts with at least 50 child utterances (TD 576, LT 408, ASD 136), by year of age and group. These are descriptive reference values from English corpora, not Thai norms. Script: `scripts/evaluate_turn_taking.py`.

## 7. Usability

Not run yet: no therapists were available. `docs/PILOT_USABILITY_PROTOCOL.md` is a 45-minute session for 3–5 therapists on demonstration data: nine timed tasks, the System Usability Scale and three open questions.

## Limits

- The measures are checked on English transcripts; there is no reference tool for Thai.
- Transcription accuracy was measured on adult read speech and on a few toddlers; there is no Thai preschool corpus with audio to test on.
- None of this is clinical validation. PasaScope does not diagnose and has no Thai norms.
