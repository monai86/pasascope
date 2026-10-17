# Telling the Child from the Adults: Thai Children Aged 20–24 Months

`speaker_attribution_real_children.md` measured speaker attribution on English-speaking children
aged 2;6 to 5;6. This report repeats the measurement on Thai, with younger children.

## Data

16 video recordings from the CRSLP corpus (CHILDES EastAsian/Thai; Sorabud Rungrojsuwan): 10
Thai children aged 20.7 to 24.1 months, in toy play with a parent, recorded in Bangkok. The first
10 minutes of each (2,536 timed utterances, 27% of them the child's) were scored against the
time-bulleted CHAT transcripts. The media were downloaded through the project owner's TalkBank
account and are kept out of the repository (`.local/evaluation/crslp_media/`).

The utterance spans come from the gold transcripts, as in the English report, so these results
measure speaker attribution alone. Per-recording tables: `crslp/speaker_attribution_*_audio_only.md`.

## Results

| Backend | Accuracy | Child precision | Child recall | Child F1 | Median MLU-w shift | Median NDW shift |
|---|---|---|---|---|---|---|
| Hybrid (app default) | 61.2% | 37.4% | 64.8% | 0.47 | 1.51 words | +123% |
| Frame model alone (USC) | 61.2% | 37.4% | 64.8% | 0.47 | 1.51 words | +123% |
| Voice clusters (ECAPA) | 64.9% | 32.6% | 28.2% | 0.30 | 2.20 words | +72% |
| Calling every utterance adult | 73.0% | – | 0% | 0 | – | – |

On the English recordings the hybrid labelled 87% correctly (84% at 2;6). Here it is below the
trivial "everything is adult" baseline, and it calls many parent utterances the child's: the
child's MLU and NDW in an uncorrected draft would be inflated by adult speech.

The hybrid and the frame model give identical child labels by design: the frame model decides
who is the child, and the clusters only name the adults.

### Who is mistaken for the child?

Mothers, mostly: 20% of the mothers' 1,267 utterances were labelled as the child's, against 5% of
the fathers' 398 and at most 1% for visitors and other relatives. Brothers, sisters and child
visitors (94 utterances, 3.7%) count as "not the target child" in the gold transcripts and were
usually heard as children (72 of 94). Leaving them out changes little: accuracy 62.7%, child F1
0.49, against a 72.0% all-adult baseline.

### Is it the threshold or the model?

The frame model's child-minus-adult margin separates the two groups with an AUC of 0.67 over all
utterances (0.50 to 0.79 per recording; 0.5 is chance). Moving the decision threshold from 0 does
not help: accuracy rises toward the 73% baseline only by calling fewer utterances the child's,
and child F1 stays at or below 0.48 for every threshold from −0.4 to +0.8. The model does not
hear Thai children of this age reliably. Likely reasons: at 20–24 months many utterances are
single words, babble or vocal play; mothers speak to toddlers in a raised, child-like pitch (the
mother errors above fit this, but pitch was not measured); and the recordings are video with toys
and often several people in the room.

### Do the uncertainty flags still help?

The app marks a label "?" when the margin is under 0.3 or the utterance is under 0.5 s. Here 49%
of utterances are flagged and they hold 57% of the errors, but unflagged labels are right only
67% of the time, against about 95% on the English recordings. A clinician could not trust an
unflagged label for a child this young.

## What changed in the app

Labels are now flagged on every utterance when the child is younger than 30 months, the youngest
age at which they were checked (`MIN_CHECKED_AGE_MONTHS` in
`src/audio_pipeline/child_adult_frames.py`). The therapist then confirms each speaker in review,
which the app already requires before analysis.

## For the term paper

- Automatic speaker attribution is validated for children from 2;6 (English, 84–96% by age) and
  not for children under 2;6: on Thai toddlers it is wrong about four times in ten.
- For the youngest children the speaker column must be confirmed by hand, or the session recorded
  with a separate microphone near the child.
- A Thai child/adult model would need Thai child recordings to train or adapt on; CRSLP alone
  (10 children here) is too small to both adapt and test.
