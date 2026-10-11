from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_synthetic_thai_dialogues import DIALOGUES, gold_chat_text  # noqa: E402
from scripts.evaluate_echolalia_cue import classify, load_pairs, summarize, PAIRS_PATH  # noqa: E402
from scripts.evaluate_feature_agreement_clan import agreement, product_features  # noqa: E402
from scripts.evaluate_thai_asr import turns_from_cha  # noqa: E402
from scripts.evaluate_thai_asr_public import load_references, score_clip, summarize as summarize_public  # noqa: E402


def test_product_features_ignore_chat_annotation_codes():
    coded = "@UTF8\n@Begin\n*MOT:\twhat is that ?\n*CHI:\tthe &-um dog [/] dog is run(ning) [: running] .\n*CHI:\txxx .\n@End\n"

    features = product_features(coded)

    # the, dog, dog, is, run -- not "um", "running" or the bracket codes
    assert features["system_tokens"] == 5
    assert features["system_types"] == 4
    assert features["system_child_utterances"] == 2


def test_agreement_reports_correlation_and_bias():
    rows = pd.DataFrame(
        {
            "system_tokens": [110, 220, 330, 440],
            "clan_tokens": [100, 200, 300, 400],
        }
    )

    result = agreement(rows, "system_tokens", "clan_tokens")

    assert result["n"] == 4 and result["pearson_r"] == 1.0
    assert result["mean_difference"] == 25.0
    assert result["median_relative_difference"] == 0.1


def test_labelled_echo_pairs_are_balanced_and_scored():
    pairs = load_pairs(PAIRS_PATH)
    summary = summarize(classify(pairs))

    assert sum(pair["is_echo"] for pair in pairs) == sum(not pair["is_echo"] for pair in pairs) == 20
    assert summary["true_positive"] + summary["false_negative"] == 20
    assert summary["false_positive"] + summary["true_negative"] == 20
    # Every scripted echo kind is caught; some natural replies are over-flagged.
    assert summary["recall"] == 1.0 and summary["false_positive"] > 0


def test_public_sample_scoring():
    references = load_references("1\ta.wav\tรถ สี แดง\tx\n2\tb.wav\tแมว ตัว ใหญ่\tx\nbad line\n")
    assert references == {"a.wav": "รถ สี แดง", "b.wav": "แมว ตัว ใหญ่"}

    exact = score_clip("a", "รถ สี แดง", "รถสีแดง", audio_seconds=2.0, processing_seconds=1.0)
    wrong = score_clip("b", "แมว ตัว ใหญ่", "แมว ตัว เล็ก", audio_seconds=2.0, processing_seconds=3.0)

    assert exact["wer"] == 0.0 and exact["cer"] == 0.0
    assert 0 < wrong["wer"] <= 1 and 0 < wrong["cer"] < 1
    summary = summarize_public([exact, wrong])
    assert summary["clips"] == 2 and summary["real_time_factor"] == 1.0
    assert summary["share_clips_cer_under_10pct"] == 0.5


def test_synthetic_gold_transcripts_parse_back_to_their_scripts(tmp_path):
    sample_id, turns = DIALOGUES[0]
    path = tmp_path / f"{sample_id}.cha"
    path.write_text(gold_chat_text(turns), encoding="utf-8")

    parsed = turns_from_cha(path)

    assert [(turn.speaker, "".join(turn.text.split())) for turn in parsed] == [
        (speaker, "".join(text.split())) for speaker, text in turns
    ]
