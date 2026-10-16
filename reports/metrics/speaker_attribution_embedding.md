# Speaker Attribution: `embedding`

Recordings: 16, utterances: 2838. Gold utterance spans from the CHAT time bullets; the backend also saw each utterance text; first 10 minutes of each recording.

| Measure | Value |
|---|---|
| Utterance accuracy (child vs adult) | 71.2% |
| Child precision | 62.4% |
| Child recall | 48.4% |
| Child F1 | 0.545 |
| Median absolute MLU-w shift (predicted vs gold speakers) | 0.565 |
| Median relative NDW shift | 0.176 |
| Recordings where no child speech was found | 0 |

## Per recording

| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |
|---|---|---|---|---|---|---|---|---|
| 12083 | 30.0 | 202 | 50/64 | 56.4% | 0.228 | 1.68/3.38 | 39/107 | 16.4 |
| 22138 | 30.0 | 213 | 49/49 | 81.2% | 0.592 | 2.44/2.64 | 58/74 | 11.3 |
| 11031 | 30.0 | 139 | 61/50 | 59.0% | 0.486 | 3.08/3.81 | 81/89 | 8.6 |
| 22125 | 42.0 | 121 | 70/28 | 48.8% | 0.367 | 4.03/2.44 | 97/45 | 8.4 |
| 22161 | 42.0 | 305 | 77/78 | 82.6% | 0.658 | 2.19/2.18 | 93/97 | 11.1 |
| 11066 | 54.0 | 181 | 64/35 | 69.6% | 0.444 | 3.18/2.16 | 91/51 | 10.4 |
| 12036 | 54.0 | 175 | 56/72 | 79.4% | 0.719 | 5.32/4.49 | 135/141 | 10.9 |
| 12076 | 66.0 | 156 | 64/60 | 84.6% | 0.806 | 4.69/4.53 | 143/129 | 9.2 |
| 12040 | 30.0 | 113 | 48/32 | 62.8% | 0.475 | 4.00/4.31 | 91/77 | 7.9 |
| 12095 | 30.0 | 151 | 57/32 | 55.6% | 0.247 | 3.74/2.72 | 96/62 | 6.2 |
| 12008 | 30.0 | 254 | 73/66 | 73.6% | 0.518 | 2.41/2.88 | 95/104 | 6.6 |
| 22180 | 42.0 | 230 | 77/44 | 72.6% | 0.479 | 3.31/3.26 | 105/73 | 8.9 |
| 22103 | 42.0 | 202 | 77/42 | 69.8% | 0.487 | 3.49/3.67 | 107/90 | 7.0 |
| 22118 | 54.0 | 114 | 60/30 | 57.9% | 0.467 | 2.50/3.17 | 83/67 | 3.5 |
| 12015 | 54.0 | 142 | 51/58 | 88.0% | 0.844 | 6.96/5.93 | 114/112 | 9.2 |
| 12029 | 66.0 | 140 | 76/44 | 74.3% | 0.700 | 6.97/7.18 | 196/133 | 8.4 |

## Reading these numbers

- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR and segmentation errors are not included.
- Child precision is the share of utterances called child that really are the child; recall is the share of the child's utterances that were found. Low precision adds adult words to the child's measures; low recall drops the child's words.
- These recordings are English. They test the acoustic part of speaker separation on real child voices; Thai recordings are needed to test the Thai text rules.
