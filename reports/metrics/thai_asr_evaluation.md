# Thai ASR Evaluation

Samples scored: 6. Model: faster-whisper `medium`, language strategy `thai`, run on-device.

Error rates are relative to hand-corrected gold transcripts (lower is better). Child-only rates compare text attributed to `*CHI`, so they also count speaker-separation mistakes.

## Summary

| Measure | Mean |
|---|---|
| Word error rate, all speakers | 0.1486 |
| Character error rate, all speakers | 0.1007 |
| Absolute utterance-count difference (draft vs gold) | 5.5 |
| Word error rate, child only | 1.0 |
| Character error rate, child only | 1.0 |
| Absolute MLU-words difference (draft vs gold) | 2.875 |
| Absolute TTR difference (draft vs gold) | 0.9433 |
| Absolute echolalia-count difference | 1.8333 |
| Processing time / audio length | 0.5133 |

## Per sample

| Sample | WER all | CER all | Utterances (gold/draft) | WER child | CER child | Child utts (gold/draft) | MLU-w (gold/draft) | TTR (gold/draft) | Echolalia (gold/draft) | RTF |
|---|---|---|---|---|---|---|---|---|---|---|
| synthetic_echo_01 | 0.0 | 0.0 | 8/2 | 1.0 | 1.0 | 4/0 | 3.0/0.0 | 0.83/0.0 | 2/0 | 0.81 |
| synthetic_echo_02 | 0.3793 | 0.3173 | 8/4 | 1.0 | 1.0 | 4/0 | 2.75/0.0 | 0.91/0.0 | 3/0 | 0.42 |
| synthetic_echo_03 | 0.2581 | 0.25 | 8/2 | 1.0 | 1.0 | 4/0 | 2.75/0.0 | 1.0/0.0 | 3/0 | 0.44 |
| synthetic_plain_01 | 0.0 | 0.0 | 8/2 | 1.0 | 1.0 | 4/0 | 2.5/0.0 | 1.0/0.0 | 2/0 | 0.46 |
| synthetic_plain_02 | 0.0606 | 0.0171 | 8/2 | 1.0 | 1.0 | 4/0 | 3.25/0.0 | 1.0/0.0 | 0/0 | 0.5 |
| synthetic_plain_03 | 0.1935 | 0.0196 | 8/3 | 1.0 | 1.0 | 4/0 | 3.0/0.0 | 0.92/0.0 | 1/0 | 0.45 |

## Reading these numbers

- This is an engineering check on a small sample set, not clinical validation.
- Results describe the recordings in `data/evaluation/` only; see its README for how they were produced.
- Feature differences show how far an uncorrected draft would move a measure, which is why therapist review is required before features are used.
