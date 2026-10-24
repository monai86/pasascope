from app.schemas.clinical import Utterance, DependentTier, OrphanDependentTier
from app.services.cha_service import parse_cha_document, build_cha_text

def test_cha_parser_handles_continuation_lines():
    # Continuation line starts with a tab or spaces, followed by text.
    # It should merge into the previous speaker's utterance text.
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "*CHI:\tI see a very big and nice\n\tblue car. \x15100_900\x15",
            "@End"
        ])
    )
    assert len(parsed.utterances) == 1
    assert parsed.utterances[0].text == "I see a very big and nice blue car."
    assert parsed.utterances[0].start_ms == 100
    assert parsed.utterances[0].end_ms == 900

def test_cha_parser_preserves_dependent_tiers():
    # Dependent tiers start with % and should attach to the preceding utterance.
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "*CHI:\tBlue car. \x15100_900\x15",
            "%mor:\tadj|blue n|car",
            "%gra:\t1|2|SUBJ 2|0|ROOT",
            "@End"
        ])
    )
    assert len(parsed.utterances) == 1
    utt = parsed.utterances[0]
    assert len(utt.dependent_tiers) == 2
    assert utt.dependent_tiers[0].tier == "%mor"
    assert utt.dependent_tiers[0].raw_text == "adj|blue n|car"
    assert utt.dependent_tiers[0].line_number == 5
    assert utt.dependent_tiers[1].tier == "%gra"
    assert utt.dependent_tiers[1].raw_text == "1|2|SUBJ 2|0|ROOT"
    assert utt.dependent_tiers[1].line_number == 6

def test_cha_parser_preserves_orphan_dependent_tiers():
    # If a dependent tier appears before any speaker utterance, it is an orphan.
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "%mor:\tadj|blue n|car",
            "*CHI:\tBlue car. \x15100_900\x15",
            "@End"
        ])
    )
    # The parsed document should have orphan_dependent_tiers, let's verify how it is stored
    # In Task 1 we added: orphan_dependent_tiers: list[OrphanDependentTier] on Transcript.
    # Wait, the parse_cha_document returns a ParsedChaDocument. Let's see if ParsedChaDocument
    # needs to contain orphan_dependent_tiers and malformed_lines.
    # Yes! Let's check ParsedChaDocument fields. It currently has:
    # @dataclass
    # class ParsedChaDocument:
    #     metadata: dict
    #     utterances: list[Utterance]
    #     warnings: list[str]
    #     validation_issues: list[str]
    #
    # We should update ParsedChaDocument to also have:
    #     orphan_dependent_tiers: list[OrphanDependentTier]
    #     malformed_lines: list[dict]
    #
    # Let's write the test assuming it has these.
    assert hasattr(parsed, "orphan_dependent_tiers")
    assert len(parsed.orphan_dependent_tiers) == 1
    assert parsed.orphan_dependent_tiers[0].tier == "%mor"
    assert parsed.orphan_dependent_tiers[0].raw_text == "adj|blue n|car"
    assert parsed.orphan_dependent_tiers[0].line_number == 4

def test_cha_parser_logs_malformed_lines():
    # A line that is not metadata, speaker line, or dependent tier, and isn't a valid continuation
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "This is a malformed line that doesn't start with anything valid.",
            "*CHI:\tBlue car.",
            "@End"
        ])
    )
    assert len(parsed.malformed_lines) == 1
    assert parsed.malformed_lines[0]["raw_text"] == "This is a malformed line that doesn't start with anything valid."
    assert parsed.malformed_lines[0]["line_number"] == 4

def test_cha_parser_metadata_id_and_media():
    parsed = parse_cha_document(
        "\n".join([
            "@Begin",
            "@Languages:\teng",
            "@Participants:\tCHI Child Target_Child",
            "@ID:\teng|Demo|CHI|4;00.00|female|||Target_Child|||",
            "@Media:\tdemo_audio, audio",
            "*CHI:\tBlue car.",
            "@End"
        ])
    )
    assert parsed.metadata["ids"] == [{"code": "CHI", "raw": "eng|Demo|CHI|4;00.00|female|||Target_Child|||"}]
    assert parsed.metadata["media"] == {"name": "demo_audio", "type": "audio"}

def test_build_cha_text_exports_dependent_tiers():
    # If an utterance has dependent_tiers, build_cha_text should write them right under the utterance speaker line
    utterances = [
        Utterance(
            utterance_id="u1",
            speaker="CHI",
            text="Blue car.",
            start_ms=100,
            end_ms=900,
            dependent_tiers=[
                DependentTier(tier="%mor", raw_text="adj|blue n|car", line_number=5),
                DependentTier(tier="%gra", raw_text="1|2|SUBJ 2|0|ROOT", line_number=6)
            ]
        )
    ]
    chat = build_cha_text(
        utterances,
        language="eng",
        participants="CHI Child Target_Child",
        participant_ids=["eng|Demo|CHI|4;00.00|female|||Target_Child|||"]
    )
    assert "*CHI:\tBlue car. \x15100_900\x15" in chat
    assert "%mor:\tadj|blue n|car" in chat
    assert "%gra:\t1|2|SUBJ 2|0|ROOT" in chat


import pytest

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AttestationRequest, TranscriptUploadCha
from app.services import transcript_service
from tests.service_helpers import USER_ID, new_session


def _qa(cha_text: str, code: str):
    repo = MockRepository()
    session = new_session(repo, code)
    transcript = transcript_service.create_from_cha(
        repo, session.session_id, TranscriptUploadCha(filename="test.cha", cha_text=cha_text), actor_id=USER_ID
    )
    report = transcript_service.run_qa(repo, transcript.transcript_id, actor_id=USER_ID)
    return repo, transcript.transcript_id, report


def _codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_validation_missing_begin_end():
    # Missing @Begin or @End blocks attestation unless the therapist overrides with a reason
    repo, transcript_id, report = _qa(
        "\n".join(["@Languages:\teng", "@Participants:\tCHI Child Target_Child", "*CHI:\tHello."]), "C-VAL-1"
    )
    assert report.overall_status == "FAIL"
    assert _codes(report) & {"MISSING_BEGIN", "MISSING_END"}

    with pytest.raises(ValueError):
        transcript_service.attest(
            repo, transcript_id, AttestationRequest(reason="attesting", override_qa_failure=False), actor_id=USER_ID
        )
    attested = transcript_service.attest(
        repo,
        transcript_id,
        AttestationRequest(reason="attesting with override", override_qa_failure=True),
        actor_id=USER_ID,
    )
    assert attested.therapist_attested


def test_validation_unknown_speaker():
    _, _, report = _qa(
        "\n".join(["@Begin", "@Languages:\teng", "@Participants:\tCHI Child Target_Child", "*INV:\tHello.", "@End"]),
        "C-VAL-2",
    )
    assert report.overall_status == "FAIL"
    assert "UNKNOWN_SPEAKER" in _codes(report)


def test_validation_malformed_lines():
    _, _, report = _qa(
        "\n".join(["@Begin", "@Languages:\teng", "@Participants:\tCHI Child Target_Child", "*CHI Hello.", "@End"]),
        "C-VAL-3",
    )
    assert report.overall_status == "FAIL"
    assert "MALFORMED_LINE_SPEAKER_LIKE" in _codes(report)


def test_validation_timestamp_errors():
    header = ["@Begin", "@Languages:\teng", "@Participants:\tCHI Child Target_Child"]
    _, _, reversed_range = _qa("\n".join([*header, "*CHI:\tHello. \x15900_100\x15", "@End"]), "C-VAL-4")
    assert reversed_range.overall_status == "FAIL"
    assert "INVALID_TIMESTAMP_RANGE" in _codes(reversed_range)

    _, _, overlap = _qa(
        "\n".join([*header, "*CHI:\tFirst. \x15100_900\x15", "*CHI:\tSecond. \x15800_1200\x15", "@End"]),
        "C-VAL-4B",
    )
    assert overlap.overall_status == "FAIL"
    assert _codes(overlap) & {"TIMESTAMP_OVERLAP", "NON_MONOTONIC_TIMESTAMPS"}


def test_validation_empty_utterance():
    _, _, report = _qa(
        "\n".join(["@Begin", "@Languages:\teng", "@Participants:\tCHI Child Target_Child", "*CHI:\t", "@End"]),
        "C-VAL-5",
    )
    assert report.overall_status == "FAIL"
    assert "EMPTY_UTTERANCE" in _codes(report)
