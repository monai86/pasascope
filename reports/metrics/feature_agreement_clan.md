# Feature Agreement with CLAN

Transcripts: 1961 from 13 TalkBank corpora (TD 980, LT 408, NH 170, HL 138, ASD 136, SLI 113, DD 16). English.

Each transcript was processed by the therapist app's CHAT parser and feature provider and compared with CLAN KIDEVAL output for the same file.

## All transcripts

| Measure | n | Pearson r | Spearman rho | Mean difference (system - CLAN) | Median relative difference |
|---|---|---|---|---|---|
| Child word tokens | 1961 | 0.997 | 0.994 | 16.969 | 4.7% |
| Different words (types) | 1961 | 0.997 | 0.994 | 28.857 | 21.4% |
| Type-token ratio (samples with >= 50 tokens) | 1755 | 0.917 | 0.917 | 0.045 | 17.8% |
| Child utterances | 1961 | 0.861 | 0.658 | 37.451 | 8.7% |

## ASD transcripts only (n = 136)

| Measure | n | Pearson r | Spearman rho | Mean difference (system - CLAN) | Median relative difference |
|---|---|---|---|---|---|
| Child word tokens | 136 | 0.994 | 0.995 | 15.044 | 4.7% |
| Different words (types) | 136 | 0.991 | 0.992 | 22.529 | 15.3% |
| Type-token ratio (samples with >= 50 tokens) | 117 | 0.896 | 0.922 | 0.027 | 14.0% |
| Child utterances | 136 | 0.928 | 0.877 | 56.485 | 12.6% |

## Reading these numbers

- High correlation means the app ranks samples the same way CLAN does. A non-zero mean difference means the two tools count differently, so app values must not be compared with published CLAN-based norms.
- CLAN's utterance count is the number of utterances it accepts for MLU, which excludes some utterances the app counts.
- This checks feature computation on English CHAT transcripts. It says nothing about transcription accuracy or about Thai.
