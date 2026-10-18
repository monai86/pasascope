# Main Measures Compared with CLAN

Run on 2026-10-18. Transcripts: 1961 English child transcripts from 13 TalkBank corpora (TD 980, LT 408, NH 170, HL 138, ASD 136, SLI 113, DD 16).

App: BasicFeatureProvider v3.0.0, schema features-basic-v3, the code the desktop app runs. CLAN: UnixCLAN `kideval +t*CHI +leng` and `freq +t*CHI +b50` (on %mor lemmas when present, as the app counts), run on the same files by `scripts/evaluate_core_measures_clan.py`.

## All transcripts

| Measure | n | Same value | ICC(A,1) | Pearson r | Mean difference (app − CLAN) | 95% limits of agreement | CLAN mean |
|---|---|---|---|---|---|---|---|
| MLU-w (words per utterance) | 1960 | 94.9% | 1.0000 | 1.0000 | -0.000 | -0.002 to +0.002 | 3.9 |
| MLU50-w (first 50 utterances) | 1713 | 98.4% | 1.0000 | 1.0000 | -0.002 | -0.031 to +0.028 | 4.28 |
| NDW-100 (different words in 100 tokens) | 1688 | 96.3% | 0.9997 | 0.9997 | -0.027 | -0.408 to +0.355 | 48.81 |
| MATTR-50 (moving-average TTR) | 1755 | 94.0% | 0.9999 | 0.9999 | -0.000 | -0.003 to +0.002 | 0.59 |
| VOCD-D | 1755 | n/a | 0.9997 | 0.9997 | -0.017 | -0.831 to +0.797 | 38.0 |
| Different words (types) | 1961 | 85.5% | 1.0000 | 1.0000 | -0.216 | -2.124 to +1.691 | 130.35 |
| Child word tokens | 1961 | 97.9% | 1.0000 | 1.0000 | +0.067 | -1.030 to +1.164 | 505.41 |
| MLU utterances | 1961 | 99.7% | 1.0000 | 1.0000 | +0.003 | -0.105 to +0.111 | 118.94 |

## ASD transcripts only (n = 136)

| Measure | n | Same value | ICC(A,1) | Pearson r | Mean difference (app − CLAN) | 95% limits of agreement | CLAN mean |
|---|---|---|---|---|---|---|---|
| MLU-w (words per utterance) | 136 | 93.4% | 1.0000 | 1.0000 | -0.000 | -0.003 to +0.003 | 2.1 |
| MLU50-w (first 50 utterances) | 109 | 93.6% | 0.9982 | 0.9984 | -0.010 | -0.096 to +0.076 | 2.24 |
| NDW-100 (different words in 100 tokens) | 108 | 90.7% | 0.9994 | 0.9994 | -0.037 | -0.632 to +0.558 | 47.63 |
| MATTR-50 (moving-average TTR) | 117 | 93.2% | 0.9996 | 0.9997 | -0.000 | -0.004 to +0.003 | 0.57 |
| VOCD-D | 117 | n/a | 0.9996 | 0.9996 | -0.008 | -0.957 to +0.942 | 46.09 |
| Different words (types) | 136 | 67.6% | 1.0000 | 1.0000 | -0.213 | -1.462 to +1.036 | 131.06 |
| Child word tokens | 136 | 89.7% | 1.0000 | 1.0000 | +0.294 | -1.945 to +2.534 | 498.54 |
| MLU utterances | 136 | 98.5% | 1.0000 | 1.0000 | +0.015 | -0.222 to +0.252 | 204.93 |

## Reading these numbers

- **Same value**: the app and CLAN give the identical number (MLU-w, MLU50-w and MATTR-50 rounded to two decimals, counts exactly). VOCD-D samples words at random in both tools, so it is compared only by agreement statistics.
- **ICC(A,1)** measures absolute agreement, not just ranking: 1.0 means the two tools give the same values. Above 0.90 is conventionally excellent (Koo & Li, 2016).
- **Limits of agreement** (Bland & Altman, 1986): 95% of transcripts differ from CLAN by an amount inside this range.
- These are English transcripts. For Thai the app splits words with PyThaiNLP, where CLAN has no Thai word rules, so there is no CLAN reference to compare with.
- This checks measures computed from a transcript. Transcription accuracy is reported separately.
