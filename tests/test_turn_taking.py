"""Turn-taking measures: counted by hand on small samples."""

from packages.features.turn_taking import ADULT, CHILD, speaker_side, turn_taking


def test_responses_rate_and_turn_length_ratio():
    lines = [
        (ADULT, 4), (CHILD, 1),           # adult, child answers
        (ADULT, 3), (ADULT, 3), (CHILD, 2),  # two adult lines, one turn; child answers
        (None, 5),                        # an unassigned line is skipped
        (CHILD, 2),                       # child goes on: same turn
        (ADULT, 2),                       # adult, no answer
    ]
    result = turn_taking(lines)
    assert result.adult_utterances == 4
    assert result.child_responses == 2
    assert result.child_response_rate == 0.5
    # Turns: A4, C1, A6, C4, A2 → child 2.5 words per turn, adults 4.
    assert result.child_words_per_turn == 2.5 and result.adult_words_per_turn == 4
    assert result.mlt_ratio == 0.625


def test_no_adults_or_no_words_give_no_value():
    assert turn_taking([(CHILD, 2), (CHILD, 3)]).child_response_rate is None
    assert turn_taking([(ADULT, 0), (CHILD, 2)]).mlt_ratio is None
    assert turn_taking([]).child_responses == 0


def test_speaker_sides():
    assert speaker_side("chi") == CHILD
    assert speaker_side("MOT") == ADULT and speaker_side("INV") == ADULT
    assert speaker_side("UNK") is None
