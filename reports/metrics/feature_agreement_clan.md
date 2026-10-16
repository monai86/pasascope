# Feature Agreement with CLAN

Transcripts: 1961 from 13 TalkBank corpora (TD 980, LT 408, NH 170, HL 138, ASD 136, SLI 113, DD 16). English.

Each transcript was processed by the therapist app's CHAT parser and feature provider (BasicFeatureProvider v2.0.0, schema features-basic-v2) and compared with CLAN KIDEVAL output for the same file.

## All transcripts

| Measure | n | Same value as CLAN | Pearson r | Spearman rho | Mean difference (system - CLAN) | Median relative difference |
|---|---|---|---|---|---|---|
| Child word tokens | 1961 | 97.9% | 1.0 | 1.0 | 0.067 | 0.0% |
| Different words (types) | 1961 | 85.5% | 1.0 | 1.0 | -0.216 | 0.0% |
| Type-token ratio (samples with >= 50 tokens) | 1755 | n/a | 0.9999 | 1.0 | -0.0 | 0.0% |
| MLU utterances | 1961 | 99.7% | 1.0 | 1.0 | 0.003 | 0.0% |
| VOCD D | 1755 | n/a | 0.9997 | 1.0 | -0.02 | 0.5% |

## ASD transcripts only (n = 136)

| Measure | n | Same value as CLAN | Pearson r | Spearman rho | Mean difference (system - CLAN) | Median relative difference |
|---|---|---|---|---|---|---|
| Child word tokens | 136 | 89.7% | 1.0 | 1.0 | 0.294 | 0.0% |
| Different words (types) | 136 | 67.6% | 1.0 | 1.0 | -0.213 | 0.0% |
| Type-token ratio (samples with >= 50 tokens) | 117 | n/a | 0.9999 | 1.0 | -0.001 | 0.0% |
| MLU utterances | 136 | 98.5% | 1.0 | 1.0 | 0.015 | 0.0% |
| VOCD D | 117 | n/a | 0.9996 | 0.999 | -0.031 | 0.6% |

## Reading these numbers

- High correlation means the app ranks samples the same way CLAN does. A non-zero mean difference means the two tools count differently, so app values must not be compared with published CLAN-based norms.
- KIDEVAL counts FREQ types and tokens on %mor lemmas; the app does the same when a transcript has a %mor tier and counts word forms otherwise (Thai).
- VOCD samples at random. The app uses its own seeded generator, so its D can differ slightly from CLAN's even on identical tokens.
- This checks feature computation on English CHAT transcripts. It says nothing about transcription accuracy or about Thai.
