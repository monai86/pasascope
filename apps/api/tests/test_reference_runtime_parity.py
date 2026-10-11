"""The runtime features compared against reference bands must mean the same thing.

``reference_feature_adapter.RUNTIME_TO_CANONICAL`` maps runtime feature names
straight onto reference-cohort features. The existing parity test only checks
the research extractor against the shared extractor; nothing checked the
runtime provider that actually produces the values shown to therapists.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.services.ml_providers.reference_feature_adapter import RUNTIME_TO_CANONICAL

HEADERS = {"X-User-Id": "therapist-demo", "X-Mock-Role": "therapist"}
UTTERANCES = [
    ("THE", "what do you want ?"),
    ("CHI", "I want juice ."),
    ("THE", "more ?"),
    ("CHI", "more ."),
    ("CHI", "the dog is running ."),
    ("CHI", "xxx ."),
]


def _runtime_features() -> dict[str, float]:
    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        client = TestClient(app, headers=HEADERS)
        text = "\n".join(f"*{'THER' if speaker == 'THE' else speaker}:\t{words}" for speaker, words in UTTERANCES)
        transcript = client.post(
            "/api/v1/sessions/session_demo_001/transcripts/manual", json={"text": text}
        ).json()
        transcript_id = transcript["transcript_id"]
        client.post(f"/api/v1/transcripts/{transcript_id}/qa")
        client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"override_qa_failure": True})
        feature_set = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features").json()
    finally:
        app.dependency_overrides.clear()
    return {item["name"]: item["value"] for item in feature_set["features"]}


def _reference_features(tmp_path) -> dict[str, float]:
    pytest.importorskip("pylangacq")
    from src.chat_feature_extractor import extract_chat_features

    cha = tmp_path / "sample.cha"
    lines = [
        "@UTF8",
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Target_Child, THE Therapist",
        "@ID:\teng|sample|CHI|4;00.|||||Target_Child|||",
        "@ID:\teng|sample|THE||||||Therapist|||",
        *[f"*{speaker}:\t{words}" for speaker, words in UTTERANCES],
        "@End",
    ]
    cha.write_text("\n".join(lines) + "\n", encoding="utf-8")
    features = extract_chat_features(cha)
    assert features is not None
    return features


def test_runtime_and_reference_agree_on_the_child_utterance_count(tmp_path):
    runtime = _runtime_features()
    reference = _reference_features(tmp_path)

    assert runtime["child_utterance_count"] == reference[RUNTIME_TO_CANONICAL["child_utterance_count"]] == 4


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known divergence, needs a clinical decision before reference evidence is enabled: on this sample the "
        "runtime provider reports MLU-words 2.0 and unintelligible ratio 0.1667 (all utterances as denominator), "
        "while the extractor that builds the reference cohorts reports 3.0 and 0.25. Comparing one against bands "
        "built from the other is not valid. See KNOWN_LIMITATIONS.md."
    ),
)
@pytest.mark.parametrize("runtime_name", ["mean_length_of_utterance_words", "unintelligible_ratio"])
def test_runtime_feature_matches_the_reference_definition(tmp_path, runtime_name):
    runtime = _runtime_features()
    reference = _reference_features(tmp_path)

    assert float(runtime[runtime_name]) == pytest.approx(float(reference[RUNTIME_TO_CANONICAL[runtime_name]]), abs=0.05)
