# End-to-end Draft Accuracy: crslp

8 recordings, 3 minutes each from just before the first transcribed utterance. Pipeline: faster-whisper `medium`, strategy `thai_specialized`, the app's default child/adult attribution, CHAT-form drafts; measures with the app's CLAN rules. Nothing was corrected by hand.

| Measure | Value |
|---|---|
| Word error rate, all speakers (mean) | 85.7% |
| Character error rate, all speakers, spaces ignored (mean) | 74.6% |
| Word error rate, child's words (mean; includes speaker errors) | 123.0% |
| Child MLU-w, mean absolute difference draft vs gold | 1.32 words |
| Child MLU-w, correlation draft vs gold across recordings (Pearson) | 0.65 |
| Child MLU-w, rank correlation draft vs gold (Spearman) | -0.09 |
| Child NDW, mean relative difference | 91.2% |
| Child utterances, mean relative difference | 73.5% |
| Processing time / audio length (mean) | 0.45 |

MLU differences and correlations leave out 2 recording(s) whose draft has no child utterance: 020004a, 020001b.

| Recording | Group | Age (m) | WER all | WER child | Child utts gold/draft | MLU-w gold/draft | NDW gold/draft |
|---|---|---|---|---|---|---|---|
| 010908b | 01 | 21 | 94.2% | 100.0% | 11/3 | 1.64/3.67 | 12/10 |
| 020003b | 01 | 24 | 69.5% | 96.4% | 17/7 | 1.65/3.29 | 20/21 |
| 011123b | 03 | 24 | 85.6% | 100.0% | 6/9 | 2.50/1.78 | 10/16 |
| 010829b | 04 | 21 | 95.2% | 100.0% | 26/3 | 1.92/1.33 | 49/4 |
| 020004a | 04 | 24 | 99.2% | 100.0% | 10/0 | 2.60/0.00 | 19/0 |
| 011126a | 05 | 24 | 68.3% | 185.0% | 11/19 | 1.82/2.42 | 12/30 |
| 011126b | 05 | 24 | 74.2% | 202.4% | 11/16 | 3.73/6.06 | 16/49 |
| 020001b | 06 | 24 | 99.2% | 100.0% | 9/0 | 1.22/0.00 | 4/0 |

- The gold transcripts were coded by trained transcribers (retracings, fillers, unintelligible words);
  the draft has only what the pipeline adds automatically.
- This is the draft before therapist review; the app requires review and attestation before analysis.
