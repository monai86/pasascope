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

## Limits

- English recordings of North American children; Thai child recordings are still needed.
- Speaker attribution only: real drafts add transcription and segmentation errors.
- The frame model (USC SAIL, CC-BY-SA-4.0 weights) is downloaded on first use; without it the app
  falls back to the previous default.
