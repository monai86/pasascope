# Speaker Attribution Tuning

16 recordings, first 10 minutes each; tuned on 8 (11031, 12040, 12095, 11066, 12036, 12029, 22103, 22161), reported on the other 8. The child's first ~10 s of speech are the simulated voice sample and are left out of scoring for every strategy.

| Strategy | Setting | Tuning F1 | Held-out accuracy | Held-out child precision | Held-out child recall | Held-out child F1 |
|---|---|---|---|---|---|---|
| current default | threshold=0.5, min_fraction=0.1, min_embed=0.4 | 0.527 | 64.9% | 45.8% | 39.5% | 0.424 |
| pitch_duration | threshold=0.7, min_fraction=0.1, min_embed=0.2 | 0.700 | 56.7% | 38.3% | 53.1% | 0.445 |
| frame_model | threshold=0.4, min_fraction=0.2, min_embed=0.2 | 0.835 | 85.4% | 80.0% | 73.9% | 0.769 |
| enrolled | threshold=0.7, min_fraction=0.1, min_embed=0.2, multi_child=0.0 | 0.720 | 74.0% | 58.9% | 68.4% | 0.633 |
| enrolled_direct | min_embed=0.8, direct_cut=0.3 | 0.641 | 74.8% | 61.5% | 61.6% | 0.616 |

Utterance spans come from the gold transcripts, so these are speaker-attribution results only.
The voice sample is simulated from the session itself; a separate recording may differ.
