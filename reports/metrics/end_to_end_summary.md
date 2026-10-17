# From Recording to Child Measures: End-to-end Results

Every number here comes from the app's own pipeline run on real recordings, with nothing corrected
by hand: Whisper transcription, child/adult attribution, CHAT drafts, then the child's MLU-w and
NDW with the app's CLAN rules. The gold side is the corpus transcript of the same stretch of audio.
Run with `scripts/evaluate_end_to_end.py` (`data/evaluation/README.md`); per-recording tables are
in `end_to_end_ellisweismer.md`, `end_to_end_enni.md` and `end_to_end_crslp.md`.

## Data

| Corpus | Language | Children | Ages | Recording | Audio scored |
|---|---|---|---|---|---|
| EllisWeismer | English | 16 (8 late talkers, 8 typical) | 2;6–5;6 | play with an examiner | 5 min each |
| ENNI | English | 16 (8 SLI, 8 typical, age-matched) | 4;9–9;6 | story retelling | 10 min each |
| CRSLP | Thai | 8 recordings of 5 children | 1;9–2;0 | toy play with a parent, video | 3 min each |

## Results

| Measure | EllisWeismer | ENNI under 7 | ENNI 7 and over | CRSLP |
|---|---|---|---|---|
| Word error rate, all speakers | 36.4% | 29.0% | 16.3% | 85.7% |
| Word error rate, child's words | 61.4% | 33.7% | 66.8% | 123.0% |
| Child MLU-w, mean distance from gold | 0.59 words | 1.69 words | 2.56 words | 1.32 words |
| Child MLU-w, correlation with gold (Pearson) | 0.94 | −0.36 | 0.21 | 0.65 (6 recordings) |
| Child NDW, mean relative distance | 21.7% | 7.3% | 49.5% | 91.2% |

Character error rate for CRSLP, which does not depend on Thai word segmentation, was 74.6%.

### Do the drafts still tell the groups apart?

Cohen's d between the groups, from the gold transcripts and from the uncorrected drafts:

| Corpus | Measure | Gold | Draft |
|---|---|---|---|
| EllisWeismer (late talkers − typical) | MLU-w | −0.68 | −0.69 |
| | NDW | −0.88 | −0.38 |
| ENNI (SLI − typical) | MLU-w | −0.74 | −0.39 |
| | NDW | −0.54 | +0.25 |

## Reading these numbers

- **2;6 to 5;6 (EllisWeismer).** Child MLU from the drafts follows the gold closely: it ranks the
  children nearly in the same order (r 0.94) and keeps the gap between late talkers and typical
  children. NDW is less reliable, because transcription errors add and remove different words.
- **Older children (ENNI).** For children under 7 the words are mostly right (child WER 34%, NDW
  within 7%), but MLU depends on where utterances are cut. The gold transcripts cut stories into
  grammatical units; the app can only cut at pauses, and no pause length matched them for every
  child. ENNI children's MLU also varies little (5.5–7.1 under 7), so small errors reorder them.
  From 7 years the child is mostly heard as an adult (`speaker_attribution_real_children.md`):
  only 1,723 of the child's 4,420 words were labelled as the child's.
- **Thai toddlers (CRSLP).** Most of the speech is not transcribed correctly (CER 75%), and parents'
  speech is labelled as the child's. A draft is not usable for children this young.
- Every draft has to be corrected before analysis, and the app requires that. These numbers say
  how much correcting is needed, not what the app reports after review.

## What these runs changed in the app

- **Quiet speech.** Silero VAD heard 3 s of speech in 5 minutes of a far-field EllisWeismer
  recording and the draft had one line. Audio is now level-normalised before VAD and the speech
  threshold lowered (0.5 → 0.35). On EllisWeismer the word error rate fell from 44.2% to 36.4%
  and the drafts held 1,560 of the gold's 1,704 child words instead of 1,150
  (`end_to_end_ellisweismer_vad_default.md` is the run before the change).
- **Utterances split at pauses.** A same-speaker pause has to exceed 0.6 s to end an utterance
  (was 0.3 s). The constant in `src/audio_pipeline/segmentation.py` records the gaps tried.
- **Echoes kept.** Letting VAD pass 2 s silences gave Whisper whole exchanges at once, and it left
  out a child's immediate repetitions of the adult. That is the echolalia the app is meant to find,
  so VAD still cuts at 400 ms silences.
- **Sentences written twice.** A segment that is the same long sentence twice keeps one copy
  (at least 50 letters per copy, so short echoes are not removed). On FLEURS Thai the default
  model's CER fell from 10.1% to 6.5% (`thai_asr_public.md`).
- **Speaker labels by age.** Every speaker label is flagged for review when the child is under
  30 or over 83 months.

## Limits

- 16 + 16 + 8 recordings, a few minutes each. The pause rule and the VAD settings were tuned on
  EllisWeismer and ENNI, and those results are reported on the same recordings.
- English for children over 2. The only Thai child speech available was from toddlers.
- The scripted Thai dialogues (TTS) still transcribe almost perfectly with the Thai model (CER
  0.3%), but their drafts now have 2–3 lines instead of 8. The synthetic child voice is heard as
  an adult, so neighbouring turns are joined as one speaker. On the multilingual model (the app's
  fast mode), two of the six drafts leave out the child's echoes. That model also left them out
  with the original VAD settings on the current code.
