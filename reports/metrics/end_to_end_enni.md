# End-to-end Draft Accuracy: enni

16 recordings, 10 minutes each from just before the first transcribed utterance. Pipeline: faster-whisper `medium`, strategy `english`, the app's default child/adult attribution, CHAT-form drafts; measures with the app's CLAN rules. Nothing was corrected by hand.

| Measure | Value |
|---|---|
| Word error rate, all speakers (mean) | 22.7% |
| Character error rate, all speakers, spaces ignored (mean) | 18.2% |
| Word error rate, child's words (mean; includes speaker errors) | 50.3% |
| Child MLU-w, mean absolute difference draft vs gold | 2.12 words |
| Child MLU-w, correlation draft vs gold across recordings (Pearson) | -0.03 |
| Child MLU-w, rank correlation draft vs gold (Spearman) | -0.05 |
| Child NDW, mean relative difference | 28.4% |
| Child utterances, mean relative difference | 36.0% |
| Processing time / audio length (mean) | 0.20 |

| Group | Recordings | MLU-w gold | MLU-w draft | NDW gold | NDW draft |
|---|---|---|---|---|---|
| SLI | 8 | 6.32 | 4.71 | 149.88 | 122.12 |
| TD | 8 | 7.16 | 5.42 | 165.00 | 108.12 |

Effect size (Cohen's d, SLI minus TD):

| Measure | From gold | From draft |
|---|---|---|
| MLU-w | -0.74 | -0.39 |
| NDW | -0.54 | +0.25 |

| Recording | Group | Age (m) | WER all | WER child | Child utts gold/draft | MLU-w gold/draft | NDW gold/draft |
|---|---|---|---|---|---|---|---|
| 479 | SLI | 57 | 31.7% | 29.9% | 65/75 | 5.68/5.31 | 106/124 |
| 572 | SLI | 65 | 32.2% | 32.2% | 132/100 | 5.48/7.15 | 197/206 |
| 617 | SLI | 79 | 39.0% | 66.8% | 62/72 | 7.10/2.99 | 128/89 |
| 678 | SLI | 83 | 41.0% | 48.7% | 74/85 | 6.54/4.87 | 140/137 |
| 729 | SLI | 90 | 48.0% | 71.0% | 82/71 | 4.43/2.48 | 150/84 |
| 817 | SLI | 97 | 16.8% | 73.0% | 68/28 | 5.40/4.00 | 142/54 |
| 821 | SLI | 107 | 15.0% | 21.5% | 71/84 | 7.66/6.07 | 147/153 |
| 926 | SLI | 114 | 15.3% | 61.3% | 83/62 | 8.28/4.79 | 189/130 |
| 471 | TD | 57 | 23.0% | 23.1% | 96/85 | 6.27/6.78 | 187/184 |
| 538 | TD | 65 | 22.2% | 22.0% | 65/85 | 6.45/4.44 | 135/136 |
| 630 | TD | 82 | 20.4% | 22.9% | 62/87 | 6.19/4.41 | 119/119 |
| 645 | TD | 79 | 22.9% | 24.4% | 89/71 | 6.75/8.14 | 165/162 |
| 738 | TD | 90 | 6.4% | 57.4% | 100/49 | 7.86/7.18 | 194/128 |
| 809 | TD | 107 | 10.9% | 95.6% | 63/6 | 7.87/3.67 | 167/19 |
| 845 | TD | 97 | 9.8% | 55.2% | 72/37 | 7.06/6.76 | 173/113 |
| 906 | TD | 114 | 8.6% | 99.7% | 74/2 | 8.86/2.00 | 180/4 |

- The gold transcripts were coded by trained transcribers (retracings, fillers, unintelligible words);
  the draft has only what the pipeline adds automatically.
- This is the draft before therapist review; the app requires review and attestation before analysis.
