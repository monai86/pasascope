# Speaker Attribution: `hybrid`

Recordings: 16, utterances: 2838. Gold utterance spans from the CHAT time bullets; the backend also saw each utterance text; first 10 minutes of each recording.

| Measure | Value |
|---|---|
| Utterance accuracy (child vs adult) | 87.0% |
| Child precision | 83.5% |
| Child recall | 79.1% |
| Child F1 | 0.812 |
| Median absolute MLU-w shift (predicted vs gold speakers) | 0.217 |
| Median relative NDW shift | 0.076 |
| Recordings where no child speech was found | 0 |

## Per recording

| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |
|---|---|---|---|---|---|---|---|---|
| 12083 | 30.0 | 202 | 50/49 | 86.6% | 0.727 | 1.68/1.93 | 39/47 | 44.5 |
| 22138 | 30.0 | 213 | 49/47 | 92.5% | 0.833 | 2.44/2.54 | 58/63 | 29.5 |
| 11031 | 30.0 | 139 | 61/63 | 81.3% | 0.790 | 3.08/3.07 | 81/80 | 21.9 |
| 22125 | 42.0 | 121 | 70/59 | 81.0% | 0.822 | 4.03/4.30 | 97/93 | 22.4 |
| 22161 | 42.0 | 305 | 77/77 | 94.1% | 0.883 | 2.19/2.39 | 93/104 | 17.9 |
| 11066 | 54.0 | 181 | 64/59 | 92.8% | 0.894 | 3.18/3.19 | 91/85 | 19.5 |
| 12036 | 54.0 | 175 | 56/64 | 81.7% | 0.733 | 5.32/5.17 | 135/148 | 21.7 |
| 12076 | 66.0 | 156 | 64/61 | 93.0% | 0.912 | 4.69/4.91 | 143/140 | 17.2 |
| 12040 | 30.0 | 113 | 48/46 | 80.5% | 0.766 | 4.00/4.33 | 91/105 | 19.8 |
| 12095 | 30.0 | 151 | 57/56 | 83.4% | 0.779 | 3.74/3.57 | 96/92 | 18.6 |
| 12008 | 30.0 | 254 | 73/94 | 77.6% | 0.659 | 2.41/2.73 | 95/125 | 15.7 |
| 22180 | 42.0 | 230 | 77/51 | 84.4% | 0.719 | 3.31/3.71 | 105/86 | 15.3 |
| 22103 | 42.0 | 202 | 77/69 | 88.1% | 0.836 | 3.49/3.47 | 107/108 | 16.7 |
| 22118 | 54.0 | 114 | 60/36 | 70.2% | 0.646 | 2.50/2.75 | 83/68 | 20.3 |
| 12015 | 54.0 | 142 | 51/52 | 97.9% | 0.971 | 6.96/6.62 | 114/112 | 21.8 |
| 12029 | 66.0 | 140 | 76/74 | 98.6% | 0.987 | 6.97/7.12 | 196/194 | 18.1 |

## Reading these numbers

- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR and segmentation errors are not included.
- Child precision is the share of utterances called child that really are the child; recall is the share of the child's utterances that were found. Low precision adds adult words to the child's measures; low recall drops the child's words.
- These recordings are English. They test the acoustic part of speaker separation on real child voices; Thai recordings are needed to test the Thai text rules.
