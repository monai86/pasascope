"""Helpers of the transcript ASD screening replication: oversampling and age matching."""

from __future__ import annotations

import numpy as np

from scripts.replicate_transcript_asd_screening import age_matched, smote


def test_smote_fills_the_minority_class_with_points_between_its_members():
    rng = np.random.default_rng(0)
    X = np.array([[0.0, 0.0], [1.0, 1.0], [10.0, 10.0], [10.0, 11.0], [11.0, 10.0], [11.0, 11.0]])
    y = np.array([1, 1, 0, 0, 0, 0])
    Xs, ys = smote(X, y, rng)
    assert (ys == 1).sum() == (ys == 0).sum() == 4
    new = Xs[len(X):]
    assert ((new >= 0) & (new <= 1)).all()  # interpolated between the two minority points only


def test_age_matching_pairs_each_autistic_child_with_one_typical_child_of_similar_age():
    rows = [{"asd": 1, "age_months": 48}, {"asd": 1, "age_months": 70},
            {"asd": 0, "age_months": 45}, {"asd": 0, "age_months": 50}, {"asd": 0, "age_months": 30}]
    pairs = age_matched(rows)
    assert [(r["asd"], r["age_months"]) for r in pairs] == [(1, 48), (0, 50)]
