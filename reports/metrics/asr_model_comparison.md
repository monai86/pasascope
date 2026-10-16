# Thai ASR: Thonburian Whisper medium vs Typhoon Whisper Turbo

Both models ran on-device through faster-whisper (CTranslate2, float16 weights) with the app's
`thai_specialized` strategy, on an Apple M2, one model at a time, with no cached drafts. Typhoon
was converted with `scripts/convert_thai_whisper.sh models/typhoon-whisper-turbo-ct2
typhoon-ai/typhoon-whisper-turbo`.

| Model | Licence | Architecture |
|---|---|---|
| Thonburian Whisper (`biodatlab/whisper-th-medium-combined`), current default | Apache-2.0 | Whisper medium, 24 decoder layers |
| Typhoon Whisper Turbo (`typhoon-ai/typhoon-whisper-turbo`) | MIT | Whisper large-v3-turbo, 4 decoder layers |

## Results

| Test set | Measure | Thonburian medium | Typhoon Turbo |
|---|---|---|---|
| FLEURS Thai, 30 clips (5.4 min, adults reading formal sentences) | CER mean | **10.1%** | 17.1% |
| | CER mean, numbers written as words on both sides | **9.1%** | 12.7% |
| | Clips with CER under 10% | **73%** | 50% |
| | Processing time / audio length | 3.41 | **2.22** |
| 6 scripted therapy-style dialogues (TTS, `data/evaluation/`) | CER, all speakers | 1.2% | **0.94%** |
| | WER, all speakers | 3.9% | **3.2%** |
| | Utterance-count difference from gold | 1.33 | **0.33** |
| | Processing time / audio length | 2.80 | **1.53** |

## Reading these numbers

- Typhoon is 1.5–1.8 times faster. On the short everyday dialogues it is slightly more accurate;
  on formal read speech with names and numbers it is clearly less accurate, partly because it
  writes numbers as words ("เจ็ดสิบ" for "70", "หนึ่งเก้าสองศูนย์" for "1920"). PasaScope spells
  numbers out for CHAT anyway, so the second FLEURS row is the fairer one; Typhoon still trails.
- Both test sets are adult speech. Neither says how the models handle children's voices.
- The default stays Thonburian medium. Typhoon is the better candidate if speed matters more than
  accuracy on unusual vocabulary; its accuracy should be checked on real child recordings first.

## Hallucinated sign-offs (fixed before these runs)

A fresh run of the default model first gave a FLEURS CER of 27.4%, against 13.5% for drafts cached
before commit 33c56456. Whisper had been appending phrases nobody said after the speech
("ขอบคุณที่ติดตาม สวัสดีครับ", "บ๊ายบาย"); trimming looping tails kept one copy of each. These
segments have almost no audio behind them, so segments shorter than 0.05 s or faster than
40 letters per second are now dropped (commit 645442d0). The figures above are after the fix,
and `thai_asr_public.md` was regenerated from the fixed drafts.
