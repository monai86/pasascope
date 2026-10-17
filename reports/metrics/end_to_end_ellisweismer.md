# End-to-end Draft Accuracy: ellisweismer

16 recordings, 5 minutes each from just before the first transcribed utterance. Pipeline: faster-whisper `medium`, strategy `english`, the app's default child/adult attribution, CHAT-form drafts; measures with the app's CLAN rules. Nothing was corrected by hand.

| Measure | Value |
|---|---|
| Word error rate, all speakers (mean) | 36.4% |
| Character error rate, all speakers, spaces ignored (mean) | 29.6% |
| Word error rate, child's words (mean; includes speaker errors) | 61.4% |
| Child MLU-w, mean absolute difference draft vs gold | 0.59 words |
| Child MLU-w, correlation draft vs gold across recordings (Pearson) | 0.94 |
| Child MLU-w, rank correlation draft vs gold (Spearman) | 0.93 |
| Child NDW, mean relative difference | 21.7% |
| Child utterances, mean relative difference | 26.5% |
| Processing time / audio length (mean) | 0.20 |

| Group | Recordings | MLU-w gold | MLU-w draft | NDW gold | NDW draft |
|---|---|---|---|---|---|
| LT | 8 | 3.11 | 3.22 | 49.25 | 47.62 |
| TD | 8 | 4.46 | 4.15 | 68.62 | 59.25 |

Effect size (Cohen's d, LT minus TD):

| Measure | From gold | From draft |
|---|---|---|
| MLU-w | -0.68 | -0.69 |
| NDW | -0.88 | -0.38 |

| Recording | Group | Age (m) | WER all | WER child | Child utts gold/draft | MLU-w gold/draft | NDW gold/draft |
|---|---|---|---|---|---|---|---|
| 12083 | LT | 30 | 34.5% | 105.3% | 17/20 | 2.06/2.30 | 26/32 |
| 22138 | LT | 30 | 20.2% | 62.5% | 16/17 | 2.25/2.12 | 30/29 |
| 11031 | LT | 30 | 63.0% | 84.5% | 25/19 | 3.04/3.21 | 45/27 |
| 22125 | LT | 42 | 46.7% | 55.0% | 27/27 | 4.85/3.74 | 61/51 |
| 22161 | LT | 42 | 29.0% | 58.6% | 35/23 | 2.00/2.61 | 42/45 |
| 11066 | LT | 54 | 30.9% | 58.5% | 24/11 | 2.58/3.18 | 42/28 |
| 12036 | LT | 54 | 39.3% | 90.0% | 30/41 | 4.33/5.24 | 77/105 |
| 12076 | LT | 66 | 21.8% | 52.5% | 32/32 | 3.75/3.34 | 71/64 |
| 12040 | TD | 30 | 55.4% | 74.0% | 26/17 | 3.85/3.76 | 62/32 |
| 12095 | TD | 30 | 40.2% | 57.8% | 25/20 | 4.36/4.35 | 61/52 |
| 12008 | TD | 30 | 52.8% | 68.1% | 36/24 | 2.39/2.79 | 59/45 |
| 22180 | TD | 42 | 27.8% | 47.3% | 44/32 | 3.25/4.00 | 76/69 |
| 22103 | TD | 42 | 31.3% | 37.8% | 37/38 | 3.38/3.61 | 74/74 |
| 22118 | TD | 54 | 48.3% | 77.5% | 20/6 | 2.00/1.83 | 30/8 |
| 12015 | TD | 54 | 23.0% | 28.3% | 23/27 | 6.74/5.74 | 67/70 |
| 12029 | TD | 66 | 17.4% | 25.2% | 24/35 | 9.75/7.14 | 120/124 |

- The gold transcripts were coded by trained transcribers (retracings, fillers, unintelligible words);
  the draft has only what the pipeline adds automatically.
- This is the draft before therapist review; the app requires review and attestation before analysis.
