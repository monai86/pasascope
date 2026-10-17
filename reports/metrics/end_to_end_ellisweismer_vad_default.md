# End-to-end Draft Accuracy: ellisweismer_vad_default

16 recordings, 5 minutes each from just before the first transcribed utterance. Pipeline: faster-whisper `medium`, strategy `english`, the app's default child/adult attribution, CHAT-form drafts; measures with the app's CLAN rules. Nothing was corrected by hand.

| Measure | Value |
|---|---|
| Word error rate, all speakers (mean) | 44.2% |
| Word error rate, child's words (mean; includes speaker errors) | 70.1% |
| Child MLU-w, mean absolute difference draft vs gold | 0.65 words |
| Child MLU-w, correlation draft vs gold across recordings (Pearson) | 0.95 |
| Child MLU-w, rank correlation draft vs gold (Spearman) | 0.89 |
| Child NDW, mean relative difference | 35.5% |
| Child utterances, mean relative difference | 41.9% |
| Processing time / audio length (mean) | 0.34 |

MLU differences and correlations leave out 1 recording(s) whose draft has no child utterance: 22125.

| Recording | Group | Age (m) | WER all | WER child | Child utts gold/draft | MLU-w gold/draft | NDW gold/draft |
|---|---|---|---|---|---|---|---|
| 12083 | - | 30 | 39.0% | 89.5% | 17/9 | 2.06/2.22 | 26/18 |
| 22138 | - | 30 | 26.8% | 75.0% | 16/9 | 2.25/1.56 | 30/13 |
| 11031 | - | 30 | 67.8% | 89.3% | 25/13 | 3.04/2.54 | 45/22 |
| 22125 | - | 42 | 99.6% | 100.0% | 27/0 | 4.85/0.00 | 61/0 |
| 22161 | - | 42 | 46.0% | 77.1% | 35/16 | 2.00/2.50 | 42/32 |
| 11066 | - | 54 | 37.4% | 63.1% | 24/13 | 2.58/2.77 | 42/30 |
| 12036 | - | 54 | 38.6% | 73.9% | 30/39 | 4.33/4.49 | 77/93 |
| 12076 | - | 66 | 26.2% | 61.7% | 32/29 | 3.75/2.93 | 71/57 |
| 12040 | - | 30 | 63.1% | 84.0% | 26/10 | 3.85/2.70 | 62/22 |
| 12095 | - | 30 | 30.9% | 57.8% | 25/23 | 4.36/3.70 | 61/57 |
| 12008 | - | 30 | 55.8% | 85.7% | 36/20 | 2.39/2.50 | 59/38 |
| 22180 | - | 42 | 32.9% | 48.7% | 44/30 | 3.25/3.93 | 76/67 |
| 22103 | - | 42 | 35.2% | 46.9% | 37/42 | 3.38/3.21 | 74/81 |
| 22118 | - | 54 | 56.6% | 90.0% | 20/2 | 2.00/2.00 | 30/4 |
| 12015 | - | 54 | 31.1% | 52.8% | 23/20 | 6.74/5.40 | 67/55 |
| 12029 | - | 66 | 20.4% | 26.9% | 24/31 | 9.75/7.10 | 120/115 |

- The gold transcripts were coded by trained transcribers (retracings, fillers, unintelligible words);
  the draft has only what the pipeline adds automatically.
- This is the draft before therapist review; the app requires review and attestation before analysis.
