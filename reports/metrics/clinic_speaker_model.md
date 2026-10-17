# A Clinic's Own Child/Adult Model

Simulates the app learning from a therapist's attested sessions: a logistic regression on the
USC frame model's encoder features (`src/audio_pipeline/clinic_speaker_model.py`), trained on
some recordings and tested on a child it has not heard. Speaker spans and labels come from the
corpus transcripts, so only speaker attribution is measured. Utterance-weighted accuracy;
random picks repeated 5 times. Run with `scripts/evaluate_clinic_speaker_model.py`.

## Same clinic: trained on N other sessions of the same corpus

| Children | Frame model | N = 1 | N = 2 | N = 4 | N = 8 | N = all others |
|---|---|---|---|---|---|---|
| ENNI under 7 | 89% | 91% | 93% | 94% | 96% | 96% |
| ENNI 7 and over | 48% | 85% | 86% | 94% | 95% | 97% |
| EllisWeismer (30-66 months) | 87% | 82% | 85% | 85% | 86% | 87% |
| CRSLP (Thai) (21-24 months) | 61% | 72% | 72% | 73% | 74% | 74% |

## Another clinic: trained on the other corpora only

| Children | Frame model | Clinic model |
|---|---|---|
| ENNI under 7 | 89% | 89% |
| ENNI 7 and over | 48% | 57% |
| EllisWeismer (30-66 months) | 87% | 80% |
| CRSLP (Thai) (21-24 months) | 61% | 64% |

## Would the app switch? (its own check: each child held out in turn, all sessions)

The app compares balanced accuracy, the mean of the share of child and of adult utterances
labelled right, so a model cannot win by calling everyone adult.

| Corpus | Sessions | Children | Accuracy, frame / clinic | Balanced accuracy, frame / clinic | Adopted |
|---|---|---|---|---|---|
| enni | 16 | 16 | 70.4% / 96.4% | 75.9% / 92.6% | yes |
| ellisweismer | 16 | 16 | 86.8% / 86.5% | 85.0% / 84.7% | no |
| crslp | 16 | 10 | 61.2% / 74.2% | 62.4% / 59.9% | no |

## Reading these numbers

- Within one corpus the recordings share a task, a setting and possibly examiners, as a
  clinic's sessions share its therapists. That is what the clinic model learns: it helps most
  where the frame model fails, ENNI children of 7 and over whose voices are heard as adults.
- Trained on other corpora it does not carry over, so the app learns per clinic and never
  ships a trained model.
- Where the frame model is already good (EllisWeismer, 2;6-5;6) the clinic model ties with it
  and the app keeps the frame model.
- Thai toddlers: plain accuracy rises only by calling more utterances adult; balanced accuracy
  falls, and the app keeps the frame model.
- English and Thai-toddler recordings only; not yet tried in a Thai clinic. Labels outside
  30-83 months stay flagged for the therapist whichever model made them.
