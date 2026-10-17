# Speaker Attribution: `hybrid`

Recordings: 16, utterances: 1716. Gold utterance spans from the CHAT time bullets; the backend saw audio only.

| Measure | Value |
|---|---|
| Utterance accuracy (child vs adult) | 69.5% |
| Child precision | 95.4% |
| Child recall | 67.3% |
| Child F1 | 0.790 |
| Median absolute MLU-w shift (predicted vs gold speakers) | 0.24 |
| Median relative NDW shift | 0.171 |
| Recordings where no child speech was found | 0 |

## Per recording

| Recording | Age (m) | Utts | Child gold/pred | Accuracy | Child F1 | MLU gold/pred | NDW gold/pred | Seconds |
|---|---|---|---|---|---|---|---|---|
| 479 | 57.3 | 80 | 70/70 | 90.0% | 0.943 | 5.68/5.52 | 106/106 | 12.7 |
| 572 | 65.0 | 228 | 166/181 | 91.7% | 0.945 | 5.46/5.20 | 222/236 | 19.9 |
| 617 | 78.8 | 91 | 83/50 | 52.8% | 0.677 | 7.30/7.53 | 149/118 | 21.8 |
| 678 | 82.8 | 111 | 76/67 | 75.7% | 0.811 | 6.54/5.79 | 140/120 | 11.9 |
| 729 | 90.4 | 160 | 138/93 | 68.1% | 0.779 | 4.20/4.20 | 196/157 | 19.3 |
| 817 | 97.2 | 79 | 69/20 | 38.0% | 0.449 | 5.40/4.75 | 142/49 | 15.1 |
| 821 | 107.0 | 81 | 71/72 | 96.3% | 0.979 | 7.66/7.62 | 147/152 | 10.4 |
| 926 | 114.1 | 95 | 83/39 | 49.5% | 0.607 | 8.28/6.85 | 189/109 | 12.9 |
| 471 | 57.2 | 99 | 96/94 | 96.0% | 0.979 | 6.27/6.35 | 187/184 | 10.8 |
| 538 | 64.8 | 79 | 65/63 | 97.5% | 0.984 | 6.45/6.59 | 135/135 | 9.6 |
| 630 | 82.5 | 74 | 62/60 | 97.3% | 0.984 | 6.19/6.13 | 119/115 | 10.4 |
| 645 | 78.9 | 157 | 142/139 | 98.1% | 0.989 | 6.89/6.93 | 207/203 | 22.5 |
| 738 | 90.4 | 110 | 105/42 | 40.9% | 0.558 | 7.98/7.69 | 197/125 | 14.5 |
| 809 | 107.0 | 108 | 87/3 | 22.2% | 0.067 | 8.00/7.67 | 205/22 | 16.2 |
| 845 | 97.1 | 79 | 73/34 | 50.6% | 0.635 | 7.06/6.41 | 173/110 | 9.2 |
| 906 | 114.0 | 85 | 74/3 | 9.4% | 0.000 | 8.86/4.33 | 180/13 | 9.1 |

## Reading these numbers

- Speaker attribution only: utterance boundaries and text come from the gold transcript, so ASR and segmentation errors are not included.
- Child precision is the share of utterances called child that really are the child; recall is the share of the child's utterances that were found. Low precision adds adult words to the child's measures; low recall drops the child's words.
- These recordings are English. They test the acoustic part of speaker separation on real child voices; Thai recordings are needed to test the Thai text rules.
