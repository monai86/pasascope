# Where Does an Utterance End? An Explainable Boundary Model

The app cuts a speaker's words into utterances before measuring MLU. This report compares its
previous rule (a pause over 0.6 s) with a logistic regression on named features
(`src/audio_pipeline/utterance_boundaries.py`). Each recording (one child) was held out in turn;
the model and its decision threshold were fitted on the others. Run with
`scripts/train_utterance_boundaries.py`.

Data: 32 recordings already run through the app's Whisper and speaker attribution
(14341 same-speaker gaps, 11072 of them placed in the gold
transcript by word alignment). Word statistics: 1836 CHAT transcripts outside the test corpora,
563,280 utterances.

## Boundaries between words of the same speaker

| Method | Precision | Recall | F1 |
|---|---|---|---|
| Pause over 0.6 s (previous rule) | 0.72 | 0.61 | 0.66 |
| Boundary model | 0.86 | 0.80 | 0.83 |

F1 gain +0.17, 95% interval +0.14 to +0.20 (bootstrap over recordings).

Which features matter (same held-out procedure, model given only some features):

| Features | Precision | Recall | F1 |
|---|---|---|---|
| pause only | 0.75 | 0.59 | 0.66 |
| sound only (pause, lengthening) | 0.73 | 0.61 | 0.67 |
| words only (Whisper punctuation, word statistics) | 0.82 | 0.81 | 0.81 |
| all features | 0.86 | 0.80 | 0.83 |

## Child MLU-w per recording, from the uncorrected draft

| Children | Method | Mean distance from gold | Mean bias | Pearson r | Spearman |
|---|---|---|---|---|---|
| All | previous rule | 1.36 | -0.88 | 0.59 | 0.59 |
| All | boundary model | 1.10 | -0.57 | 0.64 | 0.63 |
| EllisWeismer (2;6-5;6) | previous rule | 0.60 | -0.09 | 0.93 | 0.93 |
| EllisWeismer (2;6-5;6) | boundary model | 0.37 | -0.06 | 0.97 | 0.97 |
| ENNI under 7 | previous rule | 1.69 | -0.80 | -0.36 | -0.29 |
| ENNI under 7 | boundary model | 1.33 | +0.19 | -0.11 | 0.17 |
| ENNI 7 and over | previous rule | 2.56 | -2.56 | 0.21 | -0.14 |
| ENNI 7 and over | boundary model | 2.33 | -2.33 | 0.08 | -0.24 |

Speaker mistakes remain in both drafts; only where utterances are cut differs. Recordings where the
model's MLU is closer to the gold than the rule's (Wilcoxon signed-rank on the distances):

- All: 21 of 32 (p = 0.011)
- EllisWeismer (2;6-5;6): 11 of 16 (p = 0.016)
- ENNI under 7: 5 of 8 (p = 0.547)
- ENNI 7 and over: 5 of 8 (p = 0.219)

## What the model weighs (final model, all recordings)

Weights are on standardised features: + pushes toward a new utterance, - toward the same one.
Intercept -4.55; decision threshold 0.35.

| Feature | ความหมาย | Weight |
|---|---|---|
| `starts_utterances` | คำถัดไปมักขึ้นต้นประโยค | +1.28 |
| `ends_utterances` | คำนี้มักอยู่ท้ายประโยค | +1.23 |
| `sentence_mark` | Whisper ใส่จุดจบประโยค | +0.78 |
| `pause` | ช่วงหยุด | +0.70 |
| `lengthening` | ลากเสียงคำสุดท้าย | +0.31 |
| `capital_next` | คำถัดไปขึ้นต้นด้วยตัวใหญ่ | +0.25 |
| `comma` | Whisper ใส่จุลภาค | +0.04 |
