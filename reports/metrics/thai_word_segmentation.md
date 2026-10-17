# Thai Word Segmentation against Transcribers

Transcripts: `.local/evaluation/crslp_media/chat` (16 recordings, 4250 utterances scored, 5 left out
because the segmenter changed their characters). Each utterance's transcriber words were joined
and segmented again by the app (`tokenize_thai_words`, pythainlp newmm).

| Measure | Value |
|---|---|
| Utterances split exactly like the transcriber | 64.6% |
| Word-boundary precision | 0.911 |
| Word-boundary recall | 0.886 |
| Word-boundary F1 | 0.898 |
| Child MLU-w, transcriber / app (mean over recordings) | 2.19 / 2.21 |
| Child MLU-w, mean absolute difference | 0.12 words |
| Child MLU-w, correlation across recordings (Pearson) | 0.955 |

| Recording | Child utterances | MLU-w transcriber | MLU-w app |
|---|---|---|---|
| 01/010908b.cha | 46 | 1.50 | 1.54 |
| 01/020003b.cha | 126 | 1.64 | 1.90 |
| 03/011123b.cha | 60 | 2.22 | 2.20 |
| 04/010829b.cha | 96 | 1.52 | 1.59 |
| 04/020004a.cha | 63 | 2.08 | 1.97 |
| 05/011126a.cha | 80 | 2.20 | 2.16 |
| 05/011126b.cha | 81 | 2.06 | 1.94 |
| 06/020001b.cha | 54 | 1.30 | 1.87 |
| 09/010822b.cha | 120 | 2.27 | 2.22 |
| 09/011121a.cha | 92 | 2.14 | 2.21 |
| 10/011126b.cha | 61 | 2.93 | 2.95 |
| 14/011120b.cha | 95 | 2.69 | 2.79 |
| 15/010823b.cha | 62 | 3.35 | 3.24 |
| 15/011122b.cha | 51 | 3.22 | 2.94 |
| 17/011122a.cha | 77 | 2.01 | 1.92 |
| 17/011122b.cha | 92 | 1.91 | 1.94 |

- One corpus and one transcription convention; another team may split compounds differently.
- Toddler speech is mostly one- and two-word utterances, so few boundaries per utterance are at
  stake. Longer utterances from older children have more.
