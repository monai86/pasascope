# Telling the Child from the Adults on Real Child Recordings

Every language measure is computed from the utterances labelled `*CHI`, so a speaker mistake moves
MLU and NDW as much as a transcription mistake does. This report measures speaker attribution on
real child speech.

## Data

16 recordings from the EllisWeismer corpus (CHILDES Clinical-Eng; Ellis Weismer et al.,
doi:10.21415/T5FP4H): 8 typically developing children and 8 late talkers aged 2;6 to 5;6, with an
examiner or a parent, in examiner play, parent play, interview and conversation sessions. The first
10 minutes of each (2,838 timed utterances in total) were scored against the time-bulleted CHAT
transcripts. The audio is English; the acoustic part of speaker attribution does not depend on the
language, but the Thai text rules are not tested here.

Utterance spans come from the gold transcripts, so these results isolate speaker attribution from
transcription and segmentation errors. Produced with `scripts/evaluate_speaker_attribution.py` and
`scripts/tune_speaker_attribution.py`; per-recording tables are in `speaker_attribution_*.md`.

## Results, all 16 recordings

| Diarizer | Utterances right | Child precision | Child recall | Child F1 | Median MLU-w shift | Median NDW shift |
|---|---|---|---|---|---|---|
| Pitch only | 59.7% | 46.1% | 79.4% | 0.584 | 0.44 words | 33% |
| ECAPA clusters, child chosen by pitch and duration (previous default) | 72.7% | 66.0% | 48.2% | 0.557 | 0.49 words | 19% |
| USC child/adult frame model per utterance | 87.0% | 83.5% | 79.1% | 0.812 | 0.22 words | 8% |
| **Hybrid: frame model decides the child, clusters name the adults (new default)** | **87.0%** | **83.5%** | **79.1%** | **0.812** | **0.22 words** | **8%** |

Giving the diarizer each utterance's text (to apply the dialogue rules) did not help: 71.2% against
72.7% without it for the previous default, and no change for the hybrid.

By age, the frame model labelled 84% of utterances correctly at 30 months, 88% at 42, 87% at 54 and
96% at 66.

## How the settings were chosen

The recordings were split into 8 for tuning and 8 held out (alternating within each age). Tuning the
cluster threshold, the minimum cluster size and the shortest utterance to embed, and choosing the
child's cluster by pitch, by the frame model or by a 10-second sample of the child's voice, gave on
the held-out half (`speaker_attribution_tuning.md`):

| Strategy | Held-out accuracy | Held-out child F1 |
|---|---|---|
| Previous default | 64.9% | 0.424 |
| Clusters, child by pitch and duration, tuned | 56.7% | 0.445 |
| Clusters, child by a voice sample of the child, tuned | 74.0% | 0.633 |
| Clusters, child by the frame model, tuned | 85.4% | 0.769 |
| Frame model per utterance, untuned | 85.4% | 0.769 |

The best clustering setting gave the same labels as the frame model on its own, so clustering adds
nothing to the child/adult decision and the frame model alone needs no tuning. Clusters are kept only
to give different adults different codes.

## Labels the therapist should check first

An utterance is flagged when the frame model's mean child-minus-adult probability is within 0.3 of
zero or the utterance is shorter than 0.5 s. Chosen on the tuning half; on the held-out half 38% of
utterances were flagged, they held 78% of the errors, and unflagged labels were 95% right. The review
page marks these rows with "?".

## Younger and older children

The same measurement on two more corpora shows where the labels stop holding:

| Corpus | Children | Ages | Utterances right | Unflagged labels right |
|---|---|---|---|---|
| CRSLP (Thai, toy play with parents) | 10 children, 16 recordings | 1;8–2;0 | 61% | 67% |
| EllisWeismer (above) | 16 | 2;6–5;6 | 87% | 95% |
| ENNI (story retelling to an examiner), younger | 8 | 4;9–6;10 | 89% | 95% |
| ENNI, older | 8 | 7;6–9;6 | 48% | 47% |

The ENNI children were 8 with SLI and 8 typically developing, chosen so the two groups have the
same ages, from the A story set. The older ENNI children were mostly heard as adults: in 6 of 8
recordings, fewer than half the child's utterances were labelled as the child's. Every label is
now flagged for children younger than 30 or older than 83 months (`MIN_CHECKED_AGE_MONTHS`,
`MAX_CHECKED_AGE_MONTHS` in `src/audio_pipeline/child_adult_frames.py`).
Details: `speaker_attribution_thai_toddlers.md`, `enni/speaker_attribution_hybrid_audio_only.md`.

## Limits

- Labels were checked from 2;6 to 6;10 only, and in English. Thai children of those ages have not
  been tested (CRSLP covers only 1;8–2;0).
- Speaker attribution only: real drafts add transcription and segmentation errors
  (`end_to_end_*.md`).
- The frame model (USC SAIL, CC-BY-SA-4.0 weights) is downloaded on first use; without it the app
  falls back to the previous default.
