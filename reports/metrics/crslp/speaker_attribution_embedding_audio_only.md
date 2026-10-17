# Speaker Attribution: `embedding`

Recordings: 16, utterances: 2536. Gold utterance spans from the CHAT time bullets; the backend saw audio only; first 10 minutes of each recording.

| Measure | Value |
|---|---|
| Utterance accuracy (child vs adult) | 64.9% |
| Child precision | 32.6% |
| Child recall | 28.2% |
| Child F1 | 0.302 |
| Median absolute MLU-w shift (predicted vs gold speakers) | 2.195 |
| Median relative NDW shift | 0.716 |
| Recordings where no child speech was found | 0 |

## Per recording

| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |
|---|---|---|---|---|---|---|---|---|
| 010908b | 21.3 | 159 | 28/35 | 65.4% | 0.127 | 1.82/6.26 | 17/81 | 22.7 |
| 020003b | 24.1 | 224 | 58/88 | 67.9% | 0.507 | 1.86/3.47 | 56/111 | 11.7 |
| 011123b | 23.8 | 130 | 31/17 | 70.8% | 0.208 | 2.77/3.88 | 39/40 | 11.7 |
| 010829b | 21.0 | 141 | 44/52 | 50.3% | 0.271 | 1.84/4.31 | 70/147 | 10.7 |
| 020004a | 24.1 | 145 | 34/29 | 62.1% | 0.127 | 2.38/5.97 | 43/74 | 17.0 |
| 011126a | 23.9 | 187 | 46/36 | 61.5% | 0.122 | 2.35/5.67 | 51/82 | 13.8 |
| 011126b | 23.9 | 179 | 45/63 | 54.2% | 0.241 | 2.47/6.63 | 61/118 | 13.0 |
| 020001b | 24.0 | 161 | 36/28 | 77.6% | 0.438 | 2.14/4.32 | 24/54 | 13.9 |
| 010822b | 20.7 | 154 | 61/37 | 54.5% | 0.286 | 2.79/5.70 | 48/98 | 12.0 |
| 011121a | 23.7 | 201 | 48/52 | 66.2% | 0.320 | 2.48/4.46 | 56/102 | 13.6 |
| 011126b | 23.9 | 181 | 36/23 | 77.3% | 0.305 | 4.25/4.35 | 75/70 | 13.8 |
| 011120b | 23.7 | 136 | 56/19 | 64.0% | 0.347 | 3.55/3.95 | 82/55 | 8.5 |
| 010823b | 20.8 | 120 | 43/24 | 69.2% | 0.448 | 3.63/4.04 | 69/59 | 7.1 |
| 011122b | 23.7 | 149 | 33/28 | 72.5% | 0.328 | 3.36/5.57 | 45/67 | 8.6 |
| 011122a | 23.7 | 131 | 39/46 | 61.1% | 0.400 | 2.49/3.43 | 45/77 | 11.0 |
| 011122b | 23.7 | 138 | 46/15 | 61.6% | 0.131 | 2.17/5.33 | 49/48 | 10.4 |

## Reading these numbers

- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR and segmentation errors are not included.
- Child precision is the share of utterances called child that really are the child; recall is the share of the child's utterances that were found. Low precision adds adult words to the child's measures; low recall drops the child's words.
- These recordings are English. They test the acoustic part of speaker separation on real child voices; Thai recordings are needed to test the Thai text rules.
