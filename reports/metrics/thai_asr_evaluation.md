# Thai ASR Evaluation

Samples scored: 6. Model: faster-whisper `medium`, language strategy `thai`, run on-device.

Error rates are relative to hand-corrected gold transcripts (lower is better). Child-only rates compare text attributed to `*CHI`, so they also count speaker-separation mistakes.

## Summary

| Measure | Mean |
|---|---|
| Word error rate, all speakers | 0.0959 |
| Character error rate, all speakers | 0.0076 |
| Absolute utterance-count difference (draft vs gold) | 0 |
| Word error rate, child only | - |
| Character error rate, child only | - |
| Absolute MLU-words difference (draft vs gold) | - |
| Absolute TTR difference (draft vs gold) | - |
| Absolute echolalia-count difference | - |
| Processing time / audio length | 0.5417 |

## Per sample

| Sample | WER all | CER all | Utterances (gold/draft) | WER child | CER child | Child utts (gold/draft) | MLU-w (gold/draft) | TTR (gold/draft) | Echolalia (gold/draft) | RTF |
|---|---|---|---|---|---|---|---|---|---|---|
| synthetic_echo_01 | 0.0968 | 0.0 | 8/8 | - | - | - | - | - | - | 0.76 |
| synthetic_echo_02 | 0.0 | 0.0 | 8/8 | - | - | - | - | - | - | 0.49 |
| synthetic_echo_03 | 0.0968 | 0.0086 | 8/8 | - | - | - | - | - | - | 0.47 |
| synthetic_plain_01 | 0.1923 | 0.0 | 8/8 | - | - | - | - | - | - | 0.44 |
| synthetic_plain_02 | 0.0606 | 0.0171 | 8/8 | - | - | - | - | - | - | 0.65 |
| synthetic_plain_03 | 0.129 | 0.0196 | 8/8 | - | - | - | - | - | - | 0.44 |

## Reading these numbers

- This is an engineering check on a small sample set, not clinical validation.
- Results describe the recordings in `data/evaluation/` only; see its README for how they were produced.
- Feature differences show how far an uncorrected draft would move a measure, which is why therapist review is required before features are used.
