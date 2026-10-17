# Speaker Attribution: `usc`

Recordings: 16, utterances: 2536. Gold utterance spans from the CHAT time bullets; the backend saw audio only; first 10 minutes of each recording.

| Measure | Value |
|---|---|
| Utterance accuracy (child vs adult) | 61.2% |
| Child precision | 37.4% |
| Child recall | 64.8% |
| Child F1 | 0.474 |
| Median absolute MLU-w shift (predicted vs gold speakers) | 1.51 |
| Median relative NDW shift | 1.226 |
| Recordings where no child speech was found | 0 |

## Per recording

| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |
|---|---|---|---|---|---|---|---|---|
| 010908b | 21.3 | 159 | 28/68 | 53.5% | 0.229 | 1.82/4.07 | 17/98 | 27.7 |
| 020003b | 24.1 | 224 | 58/91 | 66.5% | 0.497 | 1.86/3.66 | 56/120 | 17.3 |
| 011123b | 23.8 | 130 | 31/60 | 63.8% | 0.483 | 2.77/3.13 | 39/87 | 16.1 |
| 010829b | 21.0 | 141 | 44/87 | 55.3% | 0.519 | 1.84/3.46 | 70/179 | 21.0 |
| 020004a | 24.1 | 145 | 34/56 | 64.1% | 0.422 | 2.38/4.89 | 43/87 | 20.5 |
| 011126a | 23.9 | 187 | 46/108 | 61.5% | 0.532 | 2.35/3.11 | 51/129 | 20.8 |
| 011126b | 23.9 | 179 | 45/90 | 61.5% | 0.489 | 2.47/3.97 | 61/133 | 20.2 |
| 020001b | 24.0 | 161 | 36/80 | 59.0% | 0.431 | 2.14/4.60 | 24/124 | 14.7 |
| 010822b | 20.7 | 154 | 61/75 | 58.4% | 0.529 | 2.79/4.31 | 48/112 | 21.4 |
| 011121a | 23.7 | 201 | 48/84 | 61.2% | 0.409 | 2.48/4.14 | 56/137 | 20.2 |
| 011126b | 23.9 | 181 | 36/89 | 66.3% | 0.512 | 4.25/4.35 | 75/143 | 20.3 |
| 011120b | 23.7 | 136 | 56/49 | 58.1% | 0.457 | 3.55/3.49 | 82/85 | 20.6 |
| 010823b | 20.8 | 120 | 43/58 | 65.8% | 0.594 | 3.63/3.88 | 69/96 | 18.6 |
| 011122b | 23.7 | 149 | 33/53 | 66.4% | 0.419 | 3.36/4.34 | 45/99 | 12.8 |
| 011122a | 23.7 | 131 | 39/63 | 55.7% | 0.431 | 2.49/3.25 | 45/100 | 9.6 |
| 011122b | 23.7 | 138 | 46/74 | 59.4% | 0.533 | 2.17/3.77 | 49/113 | 13.1 |

## Reading these numbers

- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR and segmentation errors are not included.
- Child precision is the share of utterances called child that really are the child; recall is the share of the child's utterances that were found. Low precision adds adult words to the child's measures; low recall drops the child's words.
- These recordings are English. They test the acoustic part of speaker separation on real child voices; Thai recordings are needed to test the Thai text rules.
