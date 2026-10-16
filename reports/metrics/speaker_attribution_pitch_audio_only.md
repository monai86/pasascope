# Speaker Attribution: `pitch`

Recordings: 16, utterances: 2838. Gold utterance spans from the CHAT time bullets; the backend saw audio only; first 10 minutes of each recording.

| Measure | Value |
|---|---|
| Utterance accuracy (child vs adult) | 59.7% |
| Child precision | 46.1% |
| Child recall | 79.4% |
| Child F1 | 0.584 |
| Median absolute MLU-w shift (predicted vs gold speakers) | 0.435 |
| Median relative NDW shift | 0.332 |
| Recordings where no child speech was found | 0 |

## Per recording

| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |
|---|---|---|---|---|---|---|---|---|
| 12083 | 30.0 | 202 | 50/106 | 57.4% | 0.449 | 1.68/3.08 | 39/125 | 6.1 |
| 22138 | 30.0 | 213 | 49/97 | 70.0% | 0.562 | 2.44/3.52 | 58/130 | 5.6 |
| 11031 | 30.0 | 139 | 61/83 | 64.0% | 0.653 | 3.08/3.26 | 81/108 | 3.2 |
| 22125 | 42.0 | 121 | 70/62 | 55.4% | 0.591 | 4.03/3.07 | 97/81 | 2.5 |
| 22161 | 42.0 | 305 | 77/247 | 43.0% | 0.463 | 2.19/3.62 | 93/231 | 2.0 |
| 11066 | 54.0 | 181 | 64/83 | 66.3% | 0.585 | 3.18/3.39 | 91/113 | 2.4 |
| 12036 | 54.0 | 175 | 56/99 | 64.0% | 0.594 | 5.32/4.88 | 135/172 | 2.9 |
| 12076 | 66.0 | 156 | 64/70 | 68.0% | 0.627 | 4.69/4.38 | 143/155 | 2.2 |
| 12040 | 30.0 | 113 | 48/64 | 69.9% | 0.696 | 4.00/4.33 | 91/121 | 3.0 |
| 12095 | 30.0 | 151 | 57/78 | 63.6% | 0.593 | 3.74/3.45 | 96/109 | 2.6 |
| 12008 | 30.0 | 254 | 73/144 | 56.3% | 0.488 | 2.41/3.41 | 95/184 | 2.0 |
| 22180 | 42.0 | 230 | 77/219 | 35.6% | 0.500 | 3.31/4.33 | 105/253 | 1.7 |
| 22103 | 42.0 | 202 | 77/120 | 62.9% | 0.619 | 3.49/3.67 | 107/150 | 2.0 |
| 22118 | 54.0 | 114 | 60/62 | 84.2% | 0.853 | 2.50/2.92 | 83/97 | 4.2 |
| 12015 | 54.0 | 142 | 51/83 | 69.0% | 0.672 | 6.96/6.53 | 114/157 | 3.4 |
| 12029 | 66.0 | 140 | 76/121 | 59.3% | 0.711 | 6.97/6.11 | 196/230 | 1.9 |

## Reading these numbers

- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR and segmentation errors are not included.
- Child precision is the share of utterances called child that really are the child; recall is the share of the child's utterances that were found. Low precision adds adult words to the child's measures; low recall drops the child's words.
- These recordings are English. They test the acoustic part of speaker separation on real child voices; Thai recordings are needed to test the Thai text rules.
