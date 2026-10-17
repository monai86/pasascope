"""The speaker-attribution evaluation reads timed CHAT, matches audio and scores labels."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.evaluate_speaker_attribution import (
    ADULT,
    CHILD,
    GoldUtterance,
    main,
    read_gold,
    score,
    summarize,
)

SR = 16000


def _voice(f0: float, seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    vibrato = 1 + 0.01 * np.sin(2 * np.pi * 5 * t)
    phase = 2 * np.pi * f0 * np.cumsum(vibrato) / SR
    return sum(np.sin(k * phase) / k for k in range(1, 6)).astype("float32") * 0.2


def _dialogue(tmp_path):
    """Adult (120 Hz) and child (320 Hz) taking turns, with its gold CHAT."""
    import soundfile

    turns = [(ADULT, 1.6, "what is that ?"), (CHILD, 1.0, "a dog ."), (ADULT, 1.8, "yes a big dog ."),
             (CHILD, 1.2, "big dog run ."), (ADULT, 1.5, "where is he going ?"), (CHILD, 0.9, "home .")]
    audio, lines, cursor = [], [], 0.3
    audio.append(np.zeros(int(cursor * SR), dtype="float32"))
    for role, seconds, text in turns:
        audio.append(_voice(320 if role == CHILD else 120, seconds))
        start, end = int(cursor * 1000), int((cursor + seconds) * 1000)
        lines.append(f"*{'CHI' if role == CHILD else 'INV'}:\t{text} \x15{start}_{end}\x15")
        audio.append(np.zeros(int(0.4 * SR), dtype="float32"))
        cursor += seconds + 0.4
    (tmp_path / "media").mkdir()
    soundfile.write(tmp_path / "media" / "talk01.wav", np.concatenate(audio), SR)
    cha = tmp_path / "chat" / "talk01.cha"
    cha.parent.mkdir()
    cha.write_text(
        "@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tCHI Target_Child, INV Investigator\n"
        "@ID:\teng|test|CHI|4;00.|female|||Target_Child|||\n@Media:\ttalk01, audio\n"
        + "\n".join(lines) + "\n@End\n",
        encoding="utf-8",
    )
    return cha


def test_reads_timed_utterances_age_and_media(tmp_path):
    cha = _dialogue(tmp_path)
    utterances, age, media = read_gold(cha)
    assert len(utterances) == 6 and media == "talk01" and age == 48
    assert [u.role for u in utterances[:2]] == [ADULT, CHILD]
    assert utterances[1].start == pytest.approx(2.3)


def test_score_reports_errors_and_measure_shift():
    gold = [GoldUtterance(0, 1, CHILD, "a big dog ."), GoldUtterance(1, 2, ADULT, "look at that ."),
            GoldUtterance(2, 3, CHILD, "dog .")]
    result = score(gold, [CHILD, CHILD, ADULT])
    assert result["correct"] == 1 and result["adult_called_child"] == 1 and result["child_called_adult"] == 1
    assert result["mlu_gold"] == 2.0 and result["mlu_predicted"] == 3.0
    pooled = summarize([result])
    assert pooled["child_precision"] == 0.5 and pooled["child_recall"] == 0.5
    assert pooled["median_abs_mlu_shift"] == 1.0


def test_pitch_backend_end_to_end(tmp_path):
    _dialogue(tmp_path)
    report = tmp_path / "out"
    code = main([
        "--cha-dir", str(tmp_path / "chat"), "--audio-dir", str(tmp_path / "media"),
        "--backend", "pitch", "--text", "none", "--report-dir", str(report),
    ])
    assert code == 0
    text = (report / "speaker_attribution_pitch_audio_only.md").read_text(encoding="utf-8")
    assert "Utterance accuracy" in text and "talk01" in text
    import csv

    row = next(csv.DictReader((report / "speaker_attribution_pitch_audio_only.csv").open(encoding="utf-8")))
    assert float(row["accuracy"]) == 1.0


def test_missing_audio_is_reported(tmp_path, capsys):
    _dialogue(tmp_path)
    (tmp_path / "media" / "talk01.wav").unlink()
    assert main(["--cha-dir", str(tmp_path / "chat"), "--audio-dir", str(tmp_path / "media"),
                 "--backend", "pitch", "--report-dir", str(tmp_path / "out")]) == 1
    assert "no audio named talk01" in capsys.readouterr().out


def test_audio_claimed_by_two_transcripts_is_not_used(tmp_path, capsys):
    """Corpora reuse a child's media name across ages; a name match alone is not enough."""
    cha = _dialogue(tmp_path)
    older = tmp_path / "chat" / "older"
    older.mkdir()
    (older / "talk01.cha").write_text(cha.read_text(encoding="utf-8"), encoding="utf-8")
    assert main(["--cha-dir", str(tmp_path / "chat"), "--audio-dir", str(tmp_path / "media"),
                 "--backend", "pitch", "--report-dir", str(tmp_path / "out")]) == 1
    assert "also matches 1 other transcript" in capsys.readouterr().out


def test_same_named_recordings_are_matched_by_folder(tmp_path):
    from scripts.evaluate_speaker_attribution import find_audio

    for child in ("05", "10"):
        (tmp_path / "audio" / child).mkdir(parents=True)
        (tmp_path / "audio" / child / "011126b.mp4").write_bytes(b"x")
        (tmp_path / "chat" / child).mkdir(parents=True)
        (tmp_path / "chat" / child / "011126b.cha").write_text("", encoding="utf-8")
    found = find_audio(tmp_path / "audio", "011126b", tmp_path / "chat" / "10" / "011126b.cha", tmp_path / "chat")
    assert found == tmp_path / "audio" / "10" / "011126b.mp4"
