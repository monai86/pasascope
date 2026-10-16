# Speaker Attribution: `embedding`

Recordings: 16, utterances: 2838. Gold utterance spans from the CHAT time bullets; the backend saw audio only; first 10 minutes of each recording.

| Measure | Value |
|---|---|
| Utterance accuracy (child vs adult) | 72.7% |
| Child precision | 66.0% |
| Child recall | 48.2% |
| Child F1 | 0.557 |
| Median absolute MLU-w shift (predicted vs gold speakers) | 0.485 |
| Median relative NDW shift | 0.192 |
| Recordings where no child speech was found | 0 |

## Per recording

| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |
|---|---|---|---|---|---|---|---|---|
| 12083 | 30.0 | 202 | 50/64 | 54.5% | 0.193 | 1.68/3.56 | 39/117 | 14.1 |
| 22138 | 30.0 | 213 | 49/45 | 85.0% | 0.660 | 2.44/2.75 | 58/68 | 10.0 |
| 11031 | 30.0 | 139 | 61/51 | 59.7% | 0.500 | 3.08/3.84 | 81/97 | 6.3 |
| 22125 | 42.0 | 121 | 70/25 | 43.0% | 0.274 | 4.03/3.12 | 97/53 | 7.0 |
| 22161 | 42.0 | 305 | 77/71 | 88.8% | 0.770 | 2.19/2.39 | 93/98 | 8.7 |
| 11066 | 54.0 | 181 | 64/34 | 69.1% | 0.429 | 3.18/2.43 | 91/56 | 7.9 |
| 12036 | 54.0 | 175 | 56/68 | 80.6% | 0.726 | 5.32/4.81 | 135/142 | 8.3 |
| 12076 | 66.0 | 156 | 64/54 | 84.6% | 0.797 | 4.69/4.86 | 143/131 | 7.3 |
| 12040 | 30.0 | 113 | 48/30 | 68.1% | 0.538 | 4.00/4.37 | 91/75 | 6.5 |
| 12095 | 30.0 | 151 | 57/30 | 60.9% | 0.322 | 3.74/2.67 | 96/54 | 6.1 |
| 12008 | 30.0 | 254 | 73/55 | 73.2% | 0.469 | 2.41/2.80 | 95/89 | 6.8 |
| 22180 | 42.0 | 230 | 77/39 | 75.6% | 0.517 | 3.31/3.57 | 105/69 | 8.8 |
| 22103 | 42.0 | 202 | 77/43 | 73.3% | 0.550 | 3.49/3.75 | 107/87 | 6.8 |
| 22118 | 54.0 | 114 | 60/26 | 52.6% | 0.372 | 2.50/3.27 | 83/59 | 3.6 |
| 12015 | 54.0 | 142 | 51/59 | 90.1% | 0.873 | 6.96/6.04 | 114/116 | 7.9 |
| 12029 | 66.0 | 140 | 76/44 | 74.3% | 0.700 | 6.97/7.43 | 196/137 | 8.2 |

## Reading these numbers

- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR and segmentation errors are not included.
- Child precision is the share of utterances called child that really are the child; recall is the share of the child's utterances that were found. Low precision adds adult words to the child's measures; low recall drops the child's words.
- These recordings are English. They test the acoustic part of speaker separation on real child voices; Thai recordings are needed to test the Thai text rules.
