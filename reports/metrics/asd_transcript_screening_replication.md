# Replicating a Transcript-based ASD Screening Model

Model: Assaf, Shehabeddine & Ramesh (2025), *Scientific Reports* 15:34134. Logistic regression
on MLU (morphemes), MLT ratio (child's mean words per turn / adults'), age and sex; ASD vs TD;
TalkBank Eigsti and Nadig corpora, one transcript per child. Run with
`scripts/replicate_transcript_asd_screening.py`.

- Nadig: ASD 13 (age 43-79 months, MLU 1.66); TD 25 (age 20-53 months, MLU 2.22)
- Eigsti: ASD 16 (age 39-78 months, MLU 2.76); TD 16 (age 33-50 months, MLU 3.30)

AUC is the mean over 50 repeats of 5-fold stratified cross-validation, with the 2.5th-97.5th
percentile range; p from 200 label permutations. Coefficients are on standardised
features (positive = more likely ASD), from a model fitted to all children of that row.

| Check | Children (ASD) | AUC | Range | p | Coefficients |
|---|---|---|---|---|---|
| Nadig: as published | 38 (13) | 0.99 | 0.983-0.995 | 0.005 | mlu -0.70, mlt_ratio -0.47, age_months +2.56, male +0.18 |
| Nadig: SMOTE inside training folds | 38 (13) | 0.98 | 0.961-0.991 | 0.005 | mlu -0.78, mlt_ratio -0.58, age_months +2.55, male -0.01 |
| Nadig: language only (MLU, MLT ratio) | 38 (13) | 0.56 | 0.463-0.624 | 0.229 | mlu -0.17, mlt_ratio -0.31 |
| Nadig: age only | 38 (13) | 0.97 | 0.969-0.981 | 0.005 | age_months +2.24 |
| Nadig: sex only | 38 (13) | 0.54 | 0.485-0.587 | 0.114 | male +0.52 |
| Eigsti: as published | 32 (16) | 0.78 | 0.724-0.824 | 0.03 | mlu -0.47, mlt_ratio +0.07, age_months +1.58, male +0.14 |
| Eigsti: SMOTE inside training folds | 32 (16) | 0.79 | 0.726-0.839 | 0.015 | mlu -0.47, mlt_ratio +0.07, age_months +1.58, male +0.14 |
| Eigsti: language only (MLU, MLT ratio) | 32 (16) | 0.53 | 0.435-0.615 | 0.378 | mlu -0.58, mlt_ratio +0.20 |
| Eigsti: age only | 32 (16) | 0.86 | 0.836-0.886 | 0.005 | age_months +1.57 |
| Eigsti: sex only | 32 (16) | 0.38 | 0.236-0.492 | 0.741 | male -0.12 |
| Eigsti: language only, age-matched pairs | 14 (7) | 0.53 | 0.388-0.633 | 0.308 | mlu -0.46, mlt_ratio -0.26 |
| trained on Eigsti, tested on Nadig: published features | 38 (13) | 0.99 | single split |  | mlu -0.47, mlt_ratio +0.07, age_months +1.58, male +0.14 |
| trained on Eigsti, tested on Nadig: language only | 38 (13) | 0.60 | single split |  | mlu -0.58, mlt_ratio +0.20 |
| trained on Nadig, tested on Eigsti: published features | 32 (16) | 0.84 | single split |  | mlu -0.66, mlt_ratio -0.42, age_months +2.24, male +0.20 |
| trained on Nadig, tested on Eigsti: language only | 32 (16) | 0.57 | single split |  | mlu -0.17, mlt_ratio -0.31 |

- Nadig: 3 autistic children have a typical child within 6 months of age.
- Eigsti: 7 autistic children have a typical child within 6 months of age.

## Reading these numbers

- In both corpora the autistic children are older than the typical children (Assaf et al. note
  that this reflects the autistic children's language delay). Age alone separates the groups about
  as well as the published model, and age carries the largest coefficient in it.
- The language features alone are close to chance, and stay there in the 7 age-matched Eigsti
  pairs (Nadig has only 3). Too few matched children to say much, but nothing here shows MLU or
  turn length telling autistic from typical children of the same age.
- Oversampling before or inside the folds makes little difference here; the inflation comes from
  age being a feature, and age stays predictive across corpora because both share the design.
- A model like this would flag older children, not autism. PasaScope reports language measures
  for the therapist and does not classify (docs/TERM_PAPER_MAPPING.md).
