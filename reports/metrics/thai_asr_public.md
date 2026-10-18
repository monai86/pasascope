# Thai ASR Accuracy on Public Read Speech

Data: first 30 clips of the FLEURS Thai test split (5.4 minutes; adult speakers reading sentences; CC BY 4.0). Models: faster-whisper, run on-device; `thai-medium` is Thonburian Whisper (biodatlab/whisper-th-medium-combined, fine-tuned for Thai, Apache-2.0) converted with `scripts/convert_thai_whisper.sh`.

| Model | WER mean | WER median | CER mean | CER median | Clips with CER under 10% | Processing time / audio length |
|---|---|---|---|---|---|---|
| `small` | 89.7% | 92.9% | 27.1% | 27.3% | 3% | 0.46 |
| `medium` | 68.7% | 52.5% | 19.2% | 16.6% | 17% | 0.8 |
| `thai-medium` | 18.4% | 15.5% | 6.5% | 5.0% | 80% | 3.01 |

All three rows were transcribed afresh on 2026-10-18 with the code of the desktop app 1.7.4. In the app, **accurate** mode uses `thai-medium` and **fast** mode the multilingual `medium` with the language set to Thai.

WER is word error rate after Thai word segmentation of both the reference and the draft; CER is character error rate. A misspelt Thai word usually segments into several wrong words, so WER is much higher than CER and CER is the steadier measure.

## Reading these numbers

- The sentences are formal, with technical terms and foreign names, read by adults in quiet conditions. Therapy-session speech has simpler vocabulary but younger voices, background noise and overlapping talk, so these figures do not transfer directly.
- No speaker separation is involved; each clip has one speaker.
- This is the reason every draft transcript must be corrected and attested by the therapist before features are extracted.
