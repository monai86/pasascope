"""A decoding loop at the end of a segment is cut instead of losing the whole turn."""

from src.audio_pipeline.whisper_transcribe import (
    WordSegment,
    _keep_words_for,
    _looks_hallucinated,
    _trim_repetition_loop,
)

LOOPED = (
    "สวัสดี ครับ วันนี้ สบาย ดี ไหม สบาย ดี ครับ วันนี้ ใคร มา ส่ง แม่ มา ส่ง "
    + "แม่ มา ส่ง " * 12
    + "แม่"
)


def test_trailing_loop_is_cut_to_one_copy():
    trimmed = _trim_repetition_loop(LOOPED)
    assert trimmed.startswith("สวัสดี ครับ วันนี้ สบาย ดี ไหม")
    assert trimmed.replace(" ", "").endswith("ใครมาส่งแม่")
    assert trimmed.count("ส่ง") <= 2
    assert not _looks_hallucinated(trimmed, -0.07, 0.0)


def test_loop_without_spaces_is_cut():
    assert _trim_repetition_loop("กินข้าวกับไข่" + "อร่อยมาก" * 6) == "กินข้าวกับไข่อร่อยมาก"


def test_repetition_in_the_middle_is_kept():
    text = "ไป ไป ไป เล่น รถ กับ แม่ แล้ว ก็ กิน ขนม"
    assert _trim_repetition_loop(text) == text


def test_words_follow_the_trimmed_text():
    words = [WordSegment(text=t, start=i, end=i + 0.5, probability=0.9) for i, t in enumerate(["มา", "ส่ง", "แม่", "มา", "ส่ง"])]
    kept = _keep_words_for("มา ส่ง แม่", words)
    assert [w.text for w in kept] == ["มา", "ส่ง", "แม่"]


def test_pause_cut_inside_a_thai_word_moves_to_the_word_end():
    from src.audio_pipeline.segmentation import split_at_pauses
    from src.audio_pipeline.whisper_transcribe import UtteranceSegment

    # "สบายดีครับ" | "เมื่อเช้า": the pause is timed between "ครั" and "บ".
    pieces = [("สบาย", 0.0, 0.4), ("ดี", 0.4, 0.6), ("ครั", 0.6, 0.8), ("บ", 1.3, 1.35), ("เมื่อ", 1.36, 1.6), ("เช้า", 1.6, 1.9)]
    words = [WordSegment(text=t, start=a, end=b, probability=0.9) for t, a, b in pieces]
    segment = UtteranceSegment(start=0.0, end=1.9, text="สบายดีครับเมื่อเช้า", words=words)

    parts = split_at_pauses([segment])

    assert [p.text for p in parts] == ["สบายดีครับ", "เมื่อเช้า"]


def test_a_long_sentence_written_twice_is_kept_once():
    from src.audio_pipeline.whisper_transcribe import _collapse_doubled_sentence

    sentence = "คู่สามีภรรยาเหล่านี้อาจเลือกที่จะมีบุตรโดยวางแผนรับเลี้ยงบุตรบุญธรรม"
    assert _collapse_doubled_sentence(f"{sentence} {sentence}") == sentence
    assert _collapse_doubled_sentence("I want that one I want that one") == "I want that one I want that one"  # short: kept
    echo = "โยนลูกบอลมาให้ครูหน่อย โยนลูกบอลมาให้ครูหน่อย"  # adult sentence and the child's echo
    assert _collapse_doubled_sentence(echo) == echo
    assert _collapse_doubled_sentence(sentence) == sentence
