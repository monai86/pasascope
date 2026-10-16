# Thai ASR Evaluation

Samples scored: 6. Model: faster-whisper `medium`, language strategy `thai_specialized`, run on-device.

Error rates are relative to hand-corrected gold transcripts (lower is better). Child-only rates compare text attributed to `*CHI`, so they also count speaker-separation mistakes.

## Summary

| Measure | Mean |
|---|---|
| Word error rate, all speakers | 0.0394 |
| Character error rate, all speakers | 0.012 |
| Absolute utterance-count difference (draft vs gold) | 0.6667 |
| Word error rate, child only | - |
| Character error rate, child only | - |
| Absolute MLU-words difference (draft vs gold) | - |
| Absolute TTR difference (draft vs gold) | - |
| Absolute echolalia-count difference | - |
| Processing time / audio length | 4.8317 |

## Per sample

| Sample | WER all | CER all | Utterances (gold/draft) | WER child | CER child | Child utts (gold/draft) | MLU-w (gold/draft) | TTR (gold/draft) | Echolalia (gold/draft) | RTF |
|---|---|---|---|---|---|---|---|---|---|---|
| synthetic_echo_01 | 0.0 | 0.0 | 8/7 | - | - | - | - | - | - | 4.89 |
| synthetic_echo_02 | 0.0 | 0.0 | 8/7 | - | - | - | - | - | - | 5.21 |
| synthetic_echo_03 | 0.0645 | 0.0172 | 8/8 | - | - | - | - | - | - | 6.59 |
| synthetic_plain_01 | 0.0769 | 0.0463 | 8/8 | - | - | - | - | - | - | 2.93 |
| synthetic_plain_02 | 0.0303 | 0.0085 | 8/8 | - | - | - | - | - | - | 5.24 |
| synthetic_plain_03 | 0.0645 | 0.0 | 8/6 | - | - | - | - | - | - | 4.13 |

## Reading these numbers

- This is an engineering check on a small sample set, not clinical validation.
- Results describe the recordings in `data/evaluation/` only; see its README for how they were produced.
- Feature differences show how far an uncorrected draft would move a measure, which is why therapist review is required before features are used.
