# Thai ASR Evaluation

Samples scored: 6. Model: faster-whisper `medium`, language strategy `thai_specialized`, run on-device.

Error rates are relative to hand-corrected gold transcripts (lower is better). Child-only rates compare text attributed to `*CHI`, so they also count speaker-separation mistakes.

## Summary

| Measure | Mean |
|---|---|
| Word error rate, all speakers | 0.0212 |
| Character error rate, all speakers | 0.0029 |
| Absolute utterance-count difference (draft vs gold) | 5.6667 |
| Word error rate, child only | 1.0 |
| Character error rate, child only | 1.0 |
| Absolute MLU-words difference (draft vs gold) | 2.875 |
| Absolute TTR difference (draft vs gold) | 0.9433 |
| Absolute echolalia-count difference | 1.8333 |
| Processing time / audio length | 2.3633 |

## Per sample

| Sample | WER all | CER all | Utterances (gold/draft) | WER child | CER child | Child utts (gold/draft) | MLU-w (gold/draft) | TTR (gold/draft) | Echolalia (gold/draft) | RTF |
|---|---|---|---|---|---|---|---|---|---|---|
| synthetic_echo_01 | 0.0 | 0.0 | 8/2 | 1.0 | 1.0 | 4/0 | 3.0/0.0 | 0.83/0.0 | 2/0 | 2.61 |
| synthetic_echo_02 | 0.0 | 0.0 | 8/2 | 1.0 | 1.0 | 4/0 | 2.75/0.0 | 0.91/0.0 | 3/0 | 2.78 |
| synthetic_echo_03 | 0.0323 | 0.0086 | 8/3 | 1.0 | 1.0 | 4/0 | 2.75/0.0 | 1.0/0.0 | 3/0 | 2.06 |
| synthetic_plain_01 | 0.0 | 0.0 | 8/2 | 1.0 | 1.0 | 4/0 | 2.5/0.0 | 1.0/0.0 | 2/0 | 2.68 |
| synthetic_plain_02 | 0.0303 | 0.0085 | 8/3 | 1.0 | 1.0 | 4/0 | 3.25/0.0 | 1.0/0.0 | 0/0 | 1.97 |
| synthetic_plain_03 | 0.0645 | 0.0 | 8/2 | 1.0 | 1.0 | 4/0 | 3.0/0.0 | 0.92/0.0 | 1/0 | 2.08 |

## Reading these numbers

- This is an engineering check on a small sample set, not clinical validation.
- Results describe the recordings in `data/evaluation/` only; see its README for how they were produced.
- Feature differences show how far an uncorrected draft would move a measure, which is why therapist review is required before features are used.
