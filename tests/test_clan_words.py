"""CHAT main tiers are counted with CLAN's KIDEVAL/MLU rules."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

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


# --- Parity with CLANc itself -------------------------------------------------
# tests/fixtures/clan/clan_rules.cha exercises every rule above. The .cex files
# are CLANc 4.13 (V 01-May-2026) output for it, run by hand:
#   mlu -t%mor -bw +t*CHI clan_rules.cha
#   freq +t*CHI clan_rules.cha

FIXTURES = Path(__file__).parent / "fixtures" / "clan"


def _fixture_child_analyses():
    lines = (FIXTURES / "clan_rules.cha").read_text(encoding="utf-8").splitlines()
    return [analyze_main_tier(line.split("\t", 1)[1]) for line in lines if line.startswith("*CHI:")]


def _clan_number(text: str, pattern: str) -> float:
    return float(re.search(pattern, text).group(1))


def test_matches_clan_mlu_output():
    clan = (FIXTURES / "clan_rules.mlu.cex").read_text(encoding="utf-8")
    m = compute_language_sample_measures(_fixture_child_analyses(), kideval_exclusions=False)
    assert m.mlu_utterances == _clan_number(clan, r"utterances = (\d+)")
    assert m.mlu_word_total == _clan_number(clan, r"words = (\d+)")
    assert round(m.mlu_words, 3) == _clan_number(clan, r"Ratio of words over utterances = ([\d.]+)")
    assert round(m.mlu_words_sd, 3) == _clan_number(clan, r"Standard deviation = ([\d.]+)")


def test_matches_clan_freq_output_word_by_word():
    clan = (FIXTURES / "clan_rules.freq.cex").read_text(encoding="utf-8")
    clan_counts = Counter({w.lower(): int(n) for n, w in re.findall(r"^\s+(\d+) (\S+)$", clan, re.M)})
    analyses = _fixture_child_analyses()
    ours = Counter(word for item in analyses for word in item.words)
    assert ours == clan_counts
    m = compute_language_sample_measures(analyses, kideval_exclusions=False)
    assert m.freq_types == _clan_number(clan, r"(\d+)\s+Total number of different item types")
    assert m.freq_tokens == _clan_number(clan, r"(\d+)\s+Total number of items")
    assert round(m.ttr, 3) == _clan_number(clan, r"([\d.]+)\s+Type/Token ratio")


def test_kideval_mode_drops_exc_utterances_that_mlu_and_freq_keep():
    m = compute_language_sample_measures(_fixture_child_analyses())
    # "no more . [+ exc]" is the only difference from the stand-alone commands.
    assert (m.mlu_utterances, m.mlu_word_total, m.freq_tokens, m.freq_types) == (15, 51, 52, 33)
    assert m.excluded_utterances == 2  # [+ exc] and www
