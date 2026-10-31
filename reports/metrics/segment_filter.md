# Does the hallucination filter drop real speech?

Every segment Whisper returned was logged with what the app's filter did with it (`scripts/evaluate_segment_filter.py`), on windows of whole session recordings chosen as in the end-to-end test, from just before the first transcribed utterance (EllisWeismer 16 and ENNI 16, 5 minutes each; all 16 CRSLP recordings, 3 minutes each, where the end-to-end test used the first 8) and on the 150 LOTUSDIS clips (near microphone). A segment counts as speech when at least half of it lies inside gold utterances and as no speech when under a tenth does; the rest are unclear and left out of both counts. Gold transcripts do not mark every sound, so a few "no speech" segments may be untranscribed talk.

Candidate change: a segment dropped only because of the two probability rules (no-speech probability above 0.85, average log-probability below -1.25) is kept and flagged for the therapist instead. Empty text, repeated 4-grams and text too fast to be speech are still dropped. Decision rule, set before the results: adopt it if, on the corpora not used to choose it (ENNI, CRSLP), it recovers at least one real speech segment and adds on average at most one flagged non-speech line per 5 minutes.

| Corpus | Mode | Minutes | Segments | Speech kept / dropped | No speech kept / dropped | Child utterances (gold) | Lost now | Lost with flags | Flagged: speech / no speech / unclear | Flagged non-speech per 5 min |
|---|---|---|---|---|---|---|---|---|---|---|
| ellisweismer | accurate | 80.0 | 995 | 774 / 5 | 114 / 3 | 468 | 0 | 0 | 0 / 0 / 0 | 0.0 |
| lotusdis | accurate | 6.8 | 234 | 149 / 85 | 0 / 0 | – | 0 | 0 | 0 / 0 / 0 | 0.0 |
| lotusdis | fast | 6.8 | 168 | 146 / 22 | 0 / 0 | – | 0 | 0 | 18 / 0 / 0 | 0.0 |
| enni (held out) | accurate | 80.0 | 590 | 509 / 3 | 24 / 0 | 726 | 1 | 1 | 0 / 0 / 0 | 0.0 |
| crslp (held out) | accurate | 48.0 | 61 | 13 / 2 | 2 / 3 | 196 | 26 | 26 | 0 / 0 / 0 | 0.0 |
| crslp (held out) | fast | 48.0 | 657 | 207 / 18 | 232 / 32 | 196 | 17 | 6 | 14 / 21 / 15 | 2.19 |

Real speech dropped, by rule:

- ellisweismer accurate: {'too_fast': 5}; non-speech dropped: {'too_fast': 3}
- lotusdis accurate: {'too_fast': 83, 'repeat': 2}; non-speech dropped: none
- lotusdis fast: {'no_speech': 20, 'too_fast': 2}; non-speech dropped: none
- enni accurate: {'too_fast': 3}; non-speech dropped: none; child utterances lost now, by rule: {'repeat': 1} (segments of 13–13 s)
- crslp accurate: {'too_fast': 1, 'repeat': 1}; non-speech dropped: {'too_fast': 3}; child utterances lost now, by rule: {'repeat': 26} (segments of 33–162 s)
- crslp fast: {'too_fast': 4, 'no_speech': 14}; non-speech dropped: {'too_fast': 10, 'no_speech': 22}; child utterances lost now, by rule: {'no_speech': 16, 'too_fast': 1} (segments of 2–90 s)

Held-out corpora: 14 real speech segments recovered, 0.60 flagged non-speech lines per 5 minutes. Decision: **adopt**.

Check by text: Whisper gives one no-speech probability per 30 s decoding window, so every segment in a window shares it, and CRSLP's gold timings are rough. A flagged "no speech" segment whose letter pairs mostly appear in gold text within 5 s was said after all. Flagged non-speech lines whose text matches nothing nearby, per 5 minutes: crslp fast 0.94 (9 of 21; 12 match gold text).

