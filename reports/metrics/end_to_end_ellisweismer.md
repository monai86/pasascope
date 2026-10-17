# End-to-end Draft Accuracy: ellisweismer

16 recordings, 5 minutes each from just before the first transcribed utterance. Pipeline: faster-whisper `medium`, strategy `english`, the app's default child/adult attribution, CHAT-form drafts; measures with the app's CLAN rules. Nothing was corrected by hand.

| Measure | Value |
|---|---|
| Word error rate, all speakers (mean) | 36.2% |
| Character error rate, all speakers, spaces ignored (mean) | 29.5% |
| Word error rate, child's words (mean; includes speaker errors) | 61.7% |
| Child MLU-w, mean absolute difference draft vs gold | 0.36 words |
| Child MLU-w, correlation draft vs gold across recordings (Pearson) | 0.98 |
| Child MLU-w, rank correlation draft vs gold (Spearman) | 0.98 |
| Child NDW, mean relative difference | 21.6% |
| Child utterances, mean relative difference | 26.4% |
| Processing time / audio length (mean) | 0.17 |

| Group | Recordings | MLU-w gold | MLU-w draft | NDW gold | NDW draft |
|---|---|---|---|---|---|
| LT | 8 | 3.11 | 3.17 | 49.25 | 47.50 |
| TD | 8 | 4.46 | 4.20 | 68.62 | 59.25 |

Effect size (Cohen's d, LT minus TD):

| Measure | From gold | From draft |
|---|---|---|
| MLU-w | -0.68 | -0.59 |
| NDW | -0.88 | -0.38 |

| Recording | Group | Age (m) | WER all | WER child | Child utts gold/draft | MLU-w gold/draft | NDW gold/draft |
|---|---|---|---|---|---|---|---|
| 12083 | LT | 30 | 35.0% | 110.5% | 17/26 | 2.06/1.92 | 26/32 |
| 22138 | LT | 30 | 19.6% | 62.5% | 16/18 | 2.25/2.00 | 30/29 |
| 11031 | LT | 30 | 63.0% | 84.5% | 25/20 | 3.04/3.05 | 45/27 |
| 22125 | LT | 42 | 46.7% | 55.0% | 27/24 | 4.85/4.21 | 61/51 |
| 22161 | LT | 42 | 28.2% | 58.6% | 35/25 | 2.00/2.40 | 42/45 |
| 11066 | LT | 54 | 30.9% | 58.5% | 24/12 | 2.58/2.92 | 42/28 |
| 12036 | LT | 54 | 38.1% | 87.7% | 30/41 | 4.33/5.17 | 77/104 |
| 12076 | LT | 66 | 22.3% | 53.3% | 32/29 | 3.75/3.66 | 71/64 |
| 12040 | TD | 30 | 55.4% | 74.0% | 26/17 | 3.85/3.76 | 62/32 |
| 12095 | TD | 30 | 40.2% | 57.8% | 25/22 | 4.36/3.95 | 61/52 |
| 12008 | TD | 30 | 53.0% | 69.2% | 36/28 | 2.39/2.50 | 59/45 |
| 22180 | TD | 42 | 27.6% | 47.3% | 44/36 | 3.25/3.58 | 76/69 |
| 22103 | TD | 42 | 31.3% | 37.8% | 37/41 | 3.38/3.34 | 74/74 |
| 22118 | TD | 54 | 48.3% | 77.5% | 20/6 | 2.00/1.83 | 30/8 |
| 12015 | TD | 54 | 22.8% | 27.7% | 23/27 | 6.74/5.70 | 67/70 |
| 12029 | TD | 66 | 17.4% | 25.2% | 24/28 | 9.75/8.93 | 120/124 |

- The gold transcripts were coded by trained transcribers (retracings, fillers, unintelligible words);
  the draft has only what the pipeline adds automatically.
- This is the draft before therapist review; the app requires review and attestation before analysis.
