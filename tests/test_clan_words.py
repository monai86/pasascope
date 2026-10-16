"""CHAT main tiers are counted with CLAN's KIDEVAL/MLU rules."""

from __future__ import annotations

import pytest

from packages.cha.clan_words import analyze_main_tier, countable_words, mor_stems
from packages.features.language_sample import compute_language_sample_measures, mattr, vocd_d


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("I [/] I want cookie .", ["i", "want", "cookie"]),
        ("<I want> [/] I want cookie .", ["i", "want", "cookie"]),
        ("<he go> [//] he went home .", ["he", "went", "home"]),
        ("<a b> [///] c .", ["c"]),
        ("&-um I want .", ["i", "want"]),
        ("&+b ball .", ["ball"]),
        ("&=laughs ball .", ["ball"]),
        ("0det dog .", ["dog"]),
        ("goed [: went] home .", ["went", "home"]),
        ("(be)cause I goin(g) .", ["because", "i", "going"]),
        ("ice+cream .", ["ice+cream"]),
        ("I (.) want (2.4) it .", ["i", "want", "it"]),
        ("no: way ↑ .", ["no", "way"]),
        ("word@s:eng , ok .", ["word", "ok"]),
        ("xxx ball .", ["ball"]),
        ("\x150_1200\x15 hi .", ["hi"]),
        ("&-อือ หนู อยาก กิน", ["หนู", "อยาก", "กิน"]),
        ("<หนู อยาก> [/] หนู อยาก กิน", ["หนู", "อยาก", "กิน"]),
        ("&+ก กิน ข้าว", ["กิน", "ข้าว"]),
        ("ไปเร็วๆ", ["ไป", "เร็วๆ"]),
        ("0 .", []),
    ],
)
def test_countable_words_follow_clan(line, expected):
    assert countable_words(line) == expected


def test_codes_are_counted_like_kideval():
    line = "<he goed> [*] [//] he [/] he went [: go] [* m] . [+ gram]"
    result = analyze_main_tier(line)
    assert result.retracings == 1
    assert result.repetitions == 1
    assert result.word_errors == 3  # two words in the <...> group, then one word
    assert result.utterance_errors == 1


def test_utterance_exclusions():
    assert analyze_main_tier("ball . [+ exc]").excluded
    assert analyze_main_tier("www .").excluded
    xxx = analyze_main_tier("xxx ball .")
    assert not xxx.excluded and xxx.mlu_excluded
    assert analyze_main_tier("ball . [+ mlue]").mlu_excluded


def test_mor_stems_use_lemmas_and_skip_punctuation():
    mor = "pro:sub|I v|want-PAST n|+n|ice+n|cream aux|be&3S~neg|not cm|cm unk|xxx ."
    assert mor_stems(mor) == ["i", "want", "icecream", "be", "not"]


def _measures(lines, **kwargs):
    return compute_language_sample_measures([analyze_main_tier(line) for line in lines], **kwargs)


def test_mlu_excludes_unintelligible_utterances_but_freq_keeps_their_words():
    m = _measures(["I want cookie .", "xxx ball .", "more .", "0 ."])
    assert m.total_utterances == 3
    assert m.mlu_utterances == 2
    assert m.mlu_words == 2.0
    assert m.freq_tokens == 5


def test_self_completion_joins_the_interrupted_utterance():
    m = _measures(["I want +/.", "+, the red one ."])
    assert m.total_utterances == 1
    assert m.mlu_utterances == 1
    assert m.mlu_words == 5.0


def test_mlu_sd_uses_clans_formula():
    m = _measures(["a .", "a b c ."])
    assert m.mlu_words == 2.0
    assert m.mlu_words_sd == 1.0
    assert _measures(["a b ."]).mlu_words_sd is None


def test_mlu50_uses_first_fifty_utterances():
    m = _measures(["a ."] * 50 + ["a b c d ."] * 10)
    assert m.mlu50_utterances == 50
    assert m.mlu50_words == 1.0
    assert m.mlu_words == pytest.approx(1.5)


def test_ndw_100_needs_a_hundred_tokens():
    assert _measures(["a b c ."]).ndw_100 is None
    words = " ".join(f"w{i % 30}" for i in range(120))
    assert _measures([words]).ndw_100 == 30


def test_mattr_averages_full_windows():
    assert mattr(["a"] * 10, window=50) is None
    assert mattr(["a", "b", "a", "b"], window=2) == 1.0
    assert mattr(["a", "a", "b"], window=2) == 0.75


def test_vocd_is_reproducible_and_tracks_diversity():
    assert vocd_d(["a"] * 49) is None
    varied = [f"w{i % 80}" for i in range(400)]
    narrow = [f"w{i % 15}" for i in range(400)]
    assert vocd_d(varied) == vocd_d(varied)
    assert vocd_d(varied) > vocd_d(narrow) > 0
