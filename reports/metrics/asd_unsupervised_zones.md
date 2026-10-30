# Unsupervised clusters and age-referenced zones for ASD

Run with `scripts/evaluate_unsupervised_asd_zones.py` on `data/ml/canonical_features.parquet`,
one session per child. Measures: `mluw`, `ttr`, `question_ratio`, `echolalia_ratio`, `unintelligible_ratio`, `pronoun_reversal_count`.

## 1. Clusters found without labels

AMI is adjusted mutual information between cluster labels and each grouping (0 = chance).

| Setting | Children (ASD) | Method | k | AMI ASD | AMI corpus | AMI age band | Most ASD in one cluster (overall) |
|---|---|---|---|---|---|---|---|
| all toy-play corpora, raw measures | 627 (62) | k-means | 2 | -0.002 | 0.28 | 0.23 | 10% (10%) |
| all toy-play corpora, raw measures | 627 (62) | gaussian mixture | 2 | 0.018 | 0.02 | 0.02 | 11% (10%) |
| all toy-play corpora, raw measures | 627 (62) | ward | 2 | 0.001 | 0.29 | 0.27 | 11% (10%) |
| all toy-play corpora, raw measures | 627 (62) | k-means | 3 | 0.007 | 0.26 | 0.21 | 11% (10%) |
| all toy-play corpora, raw measures | 627 (62) | gaussian mixture | 3 | 0.014 | 0.29 | 0.23 | 12% (10%) |
| all toy-play corpora, raw measures | 627 (62) | ward | 3 | 0.011 | 0.26 | 0.24 | 12% (10%) |
| all toy-play corpora, age removed | 627 (62) | k-means | 2 | -0.000 | 0.17 | 0.20 | 11% (10%) |
| all toy-play corpora, age removed | 627 (62) | gaussian mixture | 2 | 0.004 | 0.15 | 0.11 | 12% (10%) |
| all toy-play corpora, age removed | 627 (62) | ward | 2 | 0.023 | 0.04 | 0.01 | 11% (10%) |
| all toy-play corpora, age removed | 627 (62) | k-means | 3 | 0.007 | 0.17 | 0.20 | 11% (10%) |
| all toy-play corpora, age removed | 627 (62) | gaussian mixture | 3 | 0.020 | 0.17 | 0.18 | 16% (10%) |
| all toy-play corpora, age removed | 627 (62) | ward | 3 | 0.045 | 0.22 | 0.29 | 15% (10%) |
| Eigsti only, age removed | 48 (16) | k-means | 2 | 0.066 | 0.00 | -0.03 | 50% (33%) |
| Eigsti only, age removed | 48 (16) | gaussian mixture | 2 | 0.069 | 0.00 | -0.04 | 37% (33%) |
| Eigsti only, age removed | 48 (16) | ward | 2 | -0.007 | 0.00 | -0.03 | 50% (33%) |
| Eigsti only, age removed | 48 (16) | k-means | 3 | 0.041 | 0.00 | -0.06 | 47% (33%) |
| Eigsti only, age removed | 48 (16) | gaussian mixture | 3 | 0.022 | 0.00 | -0.04 | 38% (33%) |
| Eigsti only, age removed | 48 (16) | ward | 3 | 0.005 | 0.00 | -0.04 | 50% (33%) |
| Eigsti and Nadig, age removed | 80 (25) | k-means | 2 | 0.061 | -0.01 | -0.02 | 34% (31%) |
| Eigsti and Nadig, age removed | 80 (25) | gaussian mixture | 2 | 0.071 | -0.01 | -0.02 | 35% (31%) |
| Eigsti and Nadig, age removed | 80 (25) | ward | 2 | 0.061 | -0.01 | -0.02 | 34% (31%) |
| Eigsti and Nadig, age removed | 80 (25) | k-means | 3 | 0.102 | -0.01 | 0.05 | 59% (31%) |
| Eigsti and Nadig, age removed | 80 (25) | gaussian mixture | 3 | 0.065 | 0.03 | 0.06 | 62% (31%) |
| Eigsti and Nadig, age removed | 80 (25) | ward | 3 | 0.066 | 0.00 | 0.08 | 58% (31%) |

## 2. Below the 10th percentile of typical children the same age

Reference: TD and NH toy-play children from other corpora, within 6 months of age, at least 20 per child. A calibrated zone holds about 10% of typical children.

| Measure | Group | Corpus | Children | Median percentile | Below 10th percentile |
|---|---|---|---|---|---|
| mluw | ASD | all | 50 | 0 | 78% |
| mluw | DD | all | 14 | 33 | 14% |
| mluw | HL | all | 34 | 0 | 100% |
| mluw | LT | all | 86 | 9 | 54% |
| mluw | NH | all | 36 | 0 | 89% |
| mluw | TD | all | 199 | 42 | 27% |
| mluw | ASD | Eigsti | 12 | 25 | 42% |
| mluw | ASD | Flusberg | 3 | 0 | 100% |
| mluw | ASD | NYU-Emerson | 24 | 0 | 88% |
| mluw | ASD | Nadig | 6 | 0 | 83% |
| mluw | ASD | Rollins | 5 | 0 | 100% |
| ttr | ASD | all | 50 | 3 | 60% |
| ttr | DD | all | 14 | 60 | 7% |
| ttr | HL | all | 34 | 24 | 18% |
| ttr | LT | all | 86 | 19 | 41% |
| ttr | NH | all | 36 | 44 | 11% |
| ttr | TD | all | 199 | 52 | 10% |
| ttr | ASD | Eigsti | 12 | 75 | 25% |
| ttr | ASD | Flusberg | 3 | 3 | 67% |
| ttr | ASD | NYU-Emerson | 24 | 1 | 71% |
| ttr | ASD | Nadig | 6 | 44 | 50% |
| ttr | ASD | Rollins | 5 | 0 | 100% |

## Reading these numbers

- Clusters line up with corpus and age far more than with diagnosis; AMI with ASD stays between -0.007 and 0.102 in every setting, including after age is removed and inside the two corpora that hold both groups.
- The red zone catches language that is low for age, not autism in particular: late talkers fall in it too, and the share of autistic children in it changes a lot between corpora.
- MLU percentiles are not calibrated across corpora (typical children from the hearing-study corpora fall in the zone far more often than 10%), because transcription and utterance segmentation differ between labs.
- PasaScope therefore reports descriptive measures and gives no zone or risk label.
