# Tuning on-device transcription for the desktop app

Measured on 2026-10-16 on the development laptop: Apple M2 (4 performance +
4 efficiency cores), 16 GB, faster-whisper 1.2.1, CTranslate2 4.8.1. Other
applications were open (load average 5–12), so absolute times are noisy;
compare rows measured together.

## 1. Threads and number type

One FLEURS Thai clip (19 s, adult read speech), Thai fine-tuned `medium`
(`biodatlab/whisper-th-medium-combined`, CTranslate2), recognition only, no
word timestamps. The output text was the same length (191–192 characters)
in every row.

| Number type | Threads | Seconds |
|---|---:|---:|
| int8 | 8 (previous default) | 70.6 |
| int8 | 4 | 25.2 |
| int8_float32 | 4 | 21.0 |
| float32 | 4 | 15.6 |

Eight threads spread the work onto the efficiency cores and the whole pass
waits for them. CTranslate2's int8 kernels are slow on Apple Silicon. The app
now uses the performance-core count and float32 on Apple Silicon
(`default_cpu_threads`, `default_compute_type` in
`src/audio_pipeline/whisper_transcribe.py`), about 4.5x faster on this clip.

## 2. Word timestamps

Same clip, float32, 4 threads: 13.3–15.8 s without word timestamps, 50.2 s
with them. They are kept: the pipeline cuts utterances at pauses between
timed words before assigning speakers, which turned 1–3 utterances per
dialogue into 8 of 8 (`thai_asr_evaluation.md`).

Decoding each pause-separated stretch on its own (VAD + `clip_timestamps`)
needs no word timestamps and never cuts inside a word, but it was not faster
(48–60 s against 34–60 s for 17 s dialogues; every stretch is a full 30 s
encoder pass) and it lost context ("กินข้าวกับไข่" → "กินข้าวกับใคร"). Not used.

## 3. Thai model against the multilingual model

Six scripted Thai dialogues (`.local/evaluation/audio_samples`, TTS, about
17 s each), full pipeline, both runs on the same settings within an hour.

| Model (strategy) | Mean CER | Mean WER | Time / audio length |
|---|---:|---:|---:|
| Thai fine-tuned `medium` (`thai_specialized`) | 1.2% | 3.9% | 4.8 |
| Multilingual `medium` (`thai`) | 5.2% | 12.5% | 1.2 (0.8–0.9 after the first file) |

Files: `thai_asr_evaluation_thai_specialized.csv/.md`,
`thai_asr_evaluation_multilingual_tuned.csv`. On FLEURS the Thai model's CER
was 13.5% against 20.3%. The desktop app offers both: "แม่นยำ" (Thai model,
default) and "เร็ว" (multilingual), under ตั้งค่า → โหมดถอดเสียง.

## 4. Faults found and fixed during these runs

- A dialogue came back empty: the Thai model transcribed it correctly and then
  repeated its last phrase 13 times, and the hallucination filter dropped the
  whole segment. A trailing loop is now cut to one copy.
- Words were split across utterances ("สบายดีครั" | "บเมื่อเช้า"): the Thai
  model returns timed sub-word pieces and a pause was measured inside
  "ครับ". Pause cuts now move to the nearest Thai word boundary.

Both are covered by `tests/test_whisper_repetition_loop.py`.

## Limits

TTS dialogues use one voice per file and clear studio audio; children's
speech, overlapping turns and room noise are not represented. Times come from
one laptop under ordinary load.
