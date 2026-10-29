# Thai ASR Accuracy on Unseen Conversation (LOTUSDIS)

Data: 150 utterances drawn at random (seed 2026) from the 1,321 single-speaker utterances of 2-15 s in the LOTUSDIS test split (5,516 utterances in all; 12 adult speakers in the sample; 6.8 minutes). LOTUSDIS (NECTEC, CC BY-SA 4.0; Tipaksorn et al., 2025, arXiv:2509.18722) records unscripted three-person Thai conversations with several microphones at once. It was released in October 2025, after the last update of the Thai model (February 2024), and is not among the model's stated training data, so unlike FLEURS it cannot have been seen in training.

| App mode | Model | Microphone | CER, mean per utterance | CER, pooled | CER, Thai-script utterances (mean / pooled) | WER, mean | WER, pooled | Utterances under 10% CER | Empty drafts | Time / audio length |
|---|---|---|---|---|---|---|---|---|---|---|
| Accurate (default) | Thonburian Whisper medium | condenser, 12-15 cm | 18.3% | 18.8% | 13.6% / 13.5% | 25.6% | 25.6% | 32% | 1 | 9.29 |
| Accurate (default) | Thonburian Whisper medium | JBL device, 2 m | 25.2% | 24.9% | 20.4% / 19.9% | 33.6% | 32.8% | 23% | 3 | 10.53 |
| Fast | Whisper medium, multilingual | condenser, 12-15 cm | 28.8% | 28.1% | 24.7% / 23.8% | 43.1% | 40.8% | 20% | 11 | 1.87 |
| Fast | Whisper medium, multilingual | JBL device, 2 m | 32.6% | 33.4% | 28.1% / 28.6% | 49.3% | 48.9% | 14% | 7 | 1.79 |

Thai-script utterances: the 111 utterances whose reference has no Latin letters. LOTUSDIS writes English loanwords in Latin letters ("Cheese"), while the models usually write them in Thai ("ชีส"); that difference is a spelling convention, not a recognition error, but it counts as one in the pooled rate. Empty drafts are utterances for which the model returned no text.

The mean per utterance gives each utterance equal weight, as `thai_asr_public.md` does for FLEURS clips, so the two reports compare directly; pooled rates count all errors over all reference characters (or words). WER uses the app's Thai word segmentation of both texts; the LOTUSDIS paper used PyThaiNLP newmm, so its WER figures are close to, but not exactly comparable with, these.

## Reading these numbers

- Speakers are adults (19-48 years) in casual conversation with fillers, code-switched English words and fast turns: harder than FLEURS read speech, closer to a therapy session, but still not children.
- Overlapping talk was left out, and each utterance comes with its boundaries from the corpus, so the app's own voice detection and speaker separation are not tested here.
- Empty drafts were nearly all short utterances (2-3.5 s; one of the accurate mode's was 5.5 s). Traced on the clips the fast mode left empty: the model gave a no-speech probability above 0.85, so the app's hallucination filter dropped real speech; one more was dropped as a decoding loop (a drawn-out "โอ๊ย"). Here every clip is transcribed on its own and padded to Whisper's 30 s window; in a session the same speech sits among other speech, so this rate may not carry over. Whether short child turns are lost in whole sessions is measured by the end-to-end test.
- Time / audio length is high because each clip costs about the same time whatever its length (Whisper works in 30 s windows). It does not describe a whole session; see `asr_desktop_tuning.md` for speed.
- For comparison, the LOTUSDIS paper reports zero-shot WER of 39.5% (condenser) and 46.0% (JBL) for the larger Thonburian Whisper large-v3 model on the whole test split. This sample leaves out overlapping talk and utterances under 2 s, so lower error rates than the paper's are expected.
