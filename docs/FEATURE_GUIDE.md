# Language measures: which ones the therapist sees first, and why

The app's feature provider (`features-basic-v3`) computes 35 measures from an attested CHAT transcript. The Findings tab and the report lead with 11 **main** measures (`labels.CORE_FEATURES`). Ticking "Show all measures" shows the **supporting** and **background** ones too.

Inside the app, Knowledge → "Each measure" explains every measure: what it counts, how it helps, and what to watch for (`packages/desktop/ui/feature_guide.py`). Double-clicking a measure on the Findings tab opens its entry.

## The main measures

| Group | Measures | Why they are main |
|---|---|---|
| Sample size | child utterances, utterances in MLU, child words, unintelligible share | Whether the other values can be trusted. CLAN's KIDEVAL uses 50 or more utterances. |
| Utterance length | MLU-w | Language level and progress. The Siriraj review advises assessing the level first, then expanding from words to phrases to sentences step by step. TalkBank medians at age 4: TD 4.5, LT 3.4, ASD 2.1. |
| Vocabulary | NDW, NDW-100, MATTR-50, VOCD-D | Breadth of vocabulary; the review notes that autistic children often use a narrow range of language. NDW-100, MATTR and VOCD do not depend on sample length; TTR does, so it is a background measure. Against CLAN on 1,961 transcripts: r ≈ 1.0. |
| Turn-taking | child response rate | The review measures conversation practice by complete exchanges, not sentence length. Moves little with MLU (ρ = 0.18), so it adds something MLU does not show. |
| Review cue | echolalia cues | Echoing is common in autistic children. In TalkBank it falls with age in TD children and rises in ASD children aged 4–6. The therapist confirms each pair. |

## Turn-taking measures (new in features-basic-v3)

These are computed by `packages/features/turn_taking.py` and checked with `scripts/evaluate_turn_taking.py` (`reports/metrics/turn_taking_reference.md`). The data were TalkBank toy-play transcripts with 50 or more child utterances: 1,120 in all (TD 576, LT 408, ASD 136) from 8 corpora.

- **Child response rate** (main): adult utterances followed straight away by a child utterance, divided by all adult utterances.
  - Computed on 100% of transcripts.
  - Rises a little with age in TD (ρ = +0.18).
  - At ages 3–5, ASD medians are 0.39–0.47 against TD 0.55–0.57, and late talkers sit in between.
- **MLT ratio** (supporting): the child's mean words per turn over the adults' (Assaf et al. 2025).
  - Rises clearly with age in TD (ρ = +0.72).
  - Moves closely with MLU-w (ρ = +0.81), so it repeats much of what MLU shows.
- **Child responses** (supporting): the count behind the rate. It grows with sample length, so sessions are compared with the rate instead.

Two cautions apply to these results:
- The medians are pooled over corpora that recorded play differently, so a group difference can come from the corpus as well as from the children.
- In our replication, MLU and turn length alone separated autistic from typical children at about chance (AUC 0.53–0.56; `reports/metrics/asd_transcript_screening_replication.md`).

The app therefore describes a sample and follows change in one child; it does not classify.

## Background measures

These are kept for quality checks or are not yet trustworthy:
- **TTR:** depends on sample length.
- **MLU-m:** needs %mor, so it is not available for Thai.
- **MLU SD, MLU50:** close to MLU-w and hard to interpret clinically.
- **Analysable utterances, unknown-speaker share:** quality checks on the transcript, not information about the child.
- **Repeated-phrase cue:** overlaps the repetitions count.
- **Off-topic response cue:** needs the therapist, so it has no value.
- **The four Thai word-class counts:** experimental and not checked on child speech.

## Sources

- ภัทธาลดา จตุรวิธวงศ์. ภาษาและการพูดในเด็กที่มีภาวะออทิสติก. *Siriraj Medical Bulletin* 16(1), 2566 (2023), pp. 70–72.
- Assaf, Shehabeddine & Ramesh (2025). Screening autism spectrum disorder in children using machine learning on speech transcripts. *Scientific Reports* 15:34134.
- Rybner et al. (2022). Vocal markers of autism: assessing the generalizability of machine learning models. *Autism Research*.
- The project's own checks:
  - `reports/metrics/feature_agreement_clan.md`
  - `reports/metrics/turn_taking_reference.md`
  - `packages/desktop/ui/assets/knowledge_data.json`
