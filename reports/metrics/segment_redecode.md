# Decoding looped segments again (version 1.8.3)

When Whisper repeats one phrase for a whole window, the repeat rule drops the window and the speech in it. Since 1.8.3 such a span is decoded once more on its own (same model and settings, temperature 0); the result is filtered like the first attempt, except that lines doubted only by their scores are dropped rather than flagged, and a span that loops again is not tried a third time. Recordings without a looped segment decode exactly as before, so only those were run again; the rest of each log is copied from [`segment_filter.md`](./segment_filter.md). The setting was chosen on the CRSLP looped spans, among temperature fallback 0-0.4, a repetition penalty of 1.3 and no repeated 3-grams.

Decision rule, set before this run: adopt if at least 5 of the 26 CRSLP child utterances lost to the repeat rule come back, kept no-speech lines rise by at most one per 5 minutes, nothing gets worse on ENNI and LOTUSDIS, and the FLEURS character error rate of the accurate mode rises by at most 0.5 points.

| Set | Recordings (re-decoded) | Child utterances lost (LOTUSDIS: empty clips), before / after | Kept no-speech segments, before / after | Processing seconds, before / after | Looped spans: gold text recovered / precision |
|---|---|---|---|---|---|
| crslp accurate | 16 (4) | 26 / 5 | 2 / 5 | 1255 / 1406 | 0.38 / 0.25 |
| enni accurate | 16 (1) | 1 / 1 | 24 / 24 | 832 / 836 | 0.00 / – |
| lotusdis accurate | 150 (2) | 1 / 1 | 0 / 0 | – | – |
| ellisweismer accurate | 16 (0) | 0 / 0 | 114 / 114 | 1058 / 1058 | – |

Recall and precision count letter pairs of the gold text inside each looped span against the re-decoded text. For comparison, ordinary kept segments of the same CRSLP recordings score 0.37 / 0.28: the recovered text is as good as the rest of these toddler drafts, which is poor (`end_to_end_summary.md`).

FLEURS (30 clips, accurate mode): no segment looped, so nothing was re-decoded; character error rate 6.54%, as before (`scripts/evaluate_thai_asr_public.py`).
