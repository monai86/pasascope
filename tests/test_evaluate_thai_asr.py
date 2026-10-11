from __future__ import annotations

import csv
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_thai_asr import (  # noqa: E402
    CSV_COLUMNS,
    Turn,
    aggregate,
    draft_chat_text,
    evaluate,
    score_sample,
    turns_from_cha,
)

GOLD_CHA = "@UTF8\n@Begin\n@Languages:\ttha\n*INV:\tเล่น รถ ไหม .\n*CHI:\tเล่น รถ .\n*CHI:\tรถ สี แดง .\n@End\n"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_identical_transcripts_score_zero_error():
    turns = [Turn("INV", "เล่น รถ ไหม"), Turn("CHI", "เล่น รถ")]

    row = score_sample("s1", turns, turns)

    assert row["wer_all"] == 0.0 and row["cer_all"] == 0.0
    assert row["wer_child"] == 0.0 and row["cer_child"] == 0.0
    assert row["gold_mlu_words"] == row["hyp_mlu_words"]
    assert row["real_time_factor"] is None


def test_wrong_word_and_wrong_speaker_are_both_counted():
    gold = [Turn("INV", "เล่น รถ ไหม"), Turn("CHI", "รถ สี แดง")]
    wrong_word = [Turn("INV", "เล่น รถ ไหม"), Turn("CHI", "รถ สี ดำ")]
    wrong_speaker = [Turn("INV", "เล่น รถ ไหม"), Turn("INV", "รถ สี แดง")]

    word_row = score_sample("s1", gold, wrong_word)
    speaker_row = score_sample("s2", gold, wrong_speaker)

    assert 0 < word_row["wer_all"] < word_row["wer_child"]
    assert 0 < word_row["cer_all"] < word_row["cer_child"] < 1
    # Every word was recognised, but none of the child's speech was attributed to the child.
    assert speaker_row["wer_all"] == 0.0
    assert speaker_row["wer_child"] == 1.0
    assert speaker_row["hyp_child_utterances"] == 0


def test_child_rates_are_undefined_when_gold_has_no_child_speech():
    gold = [Turn("INV", "เล่น รถ ไหม")]

    row = score_sample("s1", gold, [Turn("CHI", "เล่น รถ ไหม")])

    assert row["wer_child"] is None and row["cer_child"] is None
    assert aggregate([row])["mean_wer_child"] is None


def test_real_time_factor_uses_processing_and_audio_time():
    turns = [Turn("CHI", "เล่น รถ")]

    row = score_sample("s1", turns, turns, audio_seconds=10.0, processing_seconds=25.0)

    assert row["real_time_factor"] == 2.5


def test_draft_chat_round_trips_through_the_parser(tmp_path):
    result = SimpleNamespace(
        utterances=[
            SimpleNamespace(speaker="INV", text="เล่น  รถ ไหม"),
            SimpleNamespace(speaker=None, text="อะไร"),
            SimpleNamespace(speaker="CHI", text="   "),
        ]
    )

    path = _write(tmp_path / "draft.cha", draft_chat_text(result))

    assert [(t.speaker, "".join(t.text.split())) for t in turns_from_cha(path)] == [
        ("INV", "เล่นรถไหม"),
        ("UNK", "อะไร"),
    ]


def test_score_only_run_writes_csv_and_markdown(tmp_path):
    evaluation_dir = tmp_path / "evaluation"
    _write(evaluation_dir / "gold_transcripts" / "clip01.cha", GOLD_CHA)
    _write(evaluation_dir / "gold_transcripts" / "clip02.cha", GOLD_CHA)
    _write(
        evaluation_dir / "hypothesis_transcripts" / "clip01.cha",
        GOLD_CHA.replace("รถ สี แดง", "รถ สี ดำ"),
    )

    rows, summary = evaluate(evaluation_dir, tmp_path / "reports", score_only=True)

    # clip02 has no saved draft, so it is skipped rather than scored as empty.
    assert [row["sample_id"] for row in rows] == ["clip01"]
    assert summary["samples"] == 1 and 0 < summary["mean_wer_all"] < 1
    with (tmp_path / "reports" / "thai_asr_evaluation.csv").open(encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert list(written[0]) == CSV_COLUMNS and written[0]["sample_id"] == "clip01"
    markdown = (tmp_path / "reports" / "thai_asr_evaluation.md").read_text(encoding="utf-8")
    assert "clip01" in markdown and "not clinical validation" in markdown


def test_no_samples_writes_no_report(tmp_path):
    rows, summary = evaluate(tmp_path / "evaluation", tmp_path / "reports", score_only=True)

    assert rows == [] and summary["samples"] == 0
    assert not (tmp_path / "reports").exists()


def test_text_only_run_blanks_speaker_dependent_figures(tmp_path):
    evaluation_dir = tmp_path / "evaluation"
    _write(evaluation_dir / "gold_transcripts" / "clip01.cha", GOLD_CHA)
    # A single-voice draft: right words, every turn attributed to one adult.
    _write(evaluation_dir / "hypothesis_transcripts" / "clip01.cha", GOLD_CHA.replace("*CHI:", "*MOT:"))

    rows, summary = evaluate(evaluation_dir, tmp_path / "reports", score_only=True, text_only=True)

    assert rows[0]["wer_all"] == 0.0 and rows[0]["cer_all"] == 0.0
    assert rows[0]["wer_child"] is None and rows[0]["hyp_mlu_words"] is None
    assert summary["mean_wer_child"] is None and summary["mean_abs_mlu_words_difference"] is None
    markdown = (tmp_path / "reports" / "thai_asr_evaluation.md").read_text(encoding="utf-8")
    assert "| clip01 | 0.0 | 0.0 | 3/3 | - | - | - | - | - | - | - |" in markdown


def test_word_scores_do_not_depend_on_spacing_inside_thai_text():
    gold = [Turn("CHI", "รถ สี แดง วิ่ง เร็ว")]

    row = score_sample("s1", gold, [Turn("CHI", "รถสีแดงวิ่งเร็ว")])

    assert row["wer_all"] == 0.0 and row["cer_all"] == 0.0
