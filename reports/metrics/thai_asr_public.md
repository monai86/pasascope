# Thai ASR Accuracy on Public Read Speech

Data: first 30 clips of the FLEURS Thai test split (5.4 minutes; adult speakers reading sentences; CC BY 4.0). Models: faster-whisper, run on-device.

| Model | WER mean | WER median | CER mean | CER median | Clips with CER under 10% | Processing time / audio length |
|---|---|---|---|---|---|---|
| `small` | 97.2% | 92.8% | 29.2% | 26.5% | 3% | 0.74 |
| `medium` | 71.4% | 62.8% | 20.3% | 16.3% | 20% | 0.97 |

WER is word error rate after Thai word segmentation of both the reference and the draft; CER is character error rate. A misspelt Thai word usually segments into several wrong words, so WER is much higher than CER and CER is the steadier measure.

## Reading these numbers

- The sentences are formal, with technical terms and foreign names, read by adults in quiet conditions. Therapy-session speech has simpler vocabulary but younger voices, background noise and overlapping talk, so these figures do not transfer directly.
- No speaker separation is involved; each clip has one speaker.
- This is the reason every draft transcript must be corrected and attested by the therapist before features are extracted.
