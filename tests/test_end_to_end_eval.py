"""The end-to-end draft evaluation compares like with like."""

from __future__ import annotations

from scripts.evaluate_end_to_end import cohens_d, evaluation_window, read_rows
from scripts.evaluate_speaker_attribution import CHILD, GoldUtterance


def test_window_starts_at_the_first_transcribed_utterance():
    """Untranscribed warm-up before the transcript is not scored against the draft."""
    utterances = [GoldUtterance(394.0, 396.0, CHILD, "hi ."), GoldUtterance(400.0, 401.0, CHILD, "yes .")]
    assert evaluation_window(utterances, 10) == (392.0, 992.0)
    assert evaluation_window([GoldUtterance(0.5, 1.0, CHILD, "hi .")], 5) == (0.0, 300.0)


def test_effect_size_and_csv_round_trip(tmp_path):
    assert round(cohens_d([1.0, 2.0, 3.0], [2.0, 3.0, 4.0]), 2) == -1.0
    assert cohens_d([1.0], [2.0, 3.0]) is None

    path = tmp_path / "rows.csv"
    path.write_text("recording,group,mlu_gold,utts_gold,mlu_draft\n0617,SLI,7.1,62,\n", encoding="utf-8")
    assert read_rows(path) == [{"group": "SLI", "recording": "0617", "mlu_gold": 7.1, "utts_gold": 62, "mlu_draft": None}]
