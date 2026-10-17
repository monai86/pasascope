"""
providers/basic_provider.py
----------------------------
BasicFeatureProvider — rule-based language sample feature extraction.

Computes descriptive linguistic features from a CHAT-parsed Transcript
using the utterance list only (no external binary required). Word and
utterance counts follow CLAN's KIDEVAL rules; see packages/cha/clan_words.py
and packages/features/language_sample.py.

All features are labelled as "review cues" or "descriptive counts";
none carry a diagnostic interpretation.  Clinical interpretation requires
a qualified therapist.

Feature schema version: features-basic-v3 (v3 adds the turn-taking measures)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Sequence

from app.schemas.clinical import (
    FeatureDefinition,
    FeatureValue,
    Transcript,
    Utterance,
)
from app.services.providers.base import (
    BaseFeatureProvider,
    FeatureExtractionResult,
    ProviderAvailability,
)
from packages.cha.clan_words import analyze_main_tier
from packages.features.thai_pos import ThaiPosCounts, thai_pos_counts
from packages.features.turn_taking import speaker_side, turn_taking
from packages.features.language_sample import (
    MATTR_WINDOW,
    RECOMMENDED_UTTERANCES,
    compute_language_sample_measures,
)


_CAUTION = (
    "This value is a descriptive language sample measure extracted by an "
    "automated prototype. It must not be used for diagnosis. Therapist "
    "interpretation is required."
)
_SCHEMA_VERSION = "features-basic-v3"
_PROVIDER_ID = "basic_feature_provider"
_PROVIDER_NAME = "BasicFeatureProvider"
_PROVIDER_VERSION = "v3.0.0"

# Minimum child utterances below which we set insufficient_data=True
_MIN_CHILD_UTTS = 3


# ---------------------------------------------------------------------------
# Feature definitions catalogue
# ---------------------------------------------------------------------------

_DEFINITIONS: list[FeatureDefinition] = [
    FeatureDefinition(
        feature_name="total_utterance_count",
        display_name="Total Utterance Count",
        description="Total number of utterances in the transcript across all speakers.",
        value_type="integer",
        unit="utterances",
        calculation_method="Count of all Utterance objects in the transcript.",
        required_inputs=["utterances"],
        limitations=["Does not exclude unintelligible utterances."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="child_utterance_count",
        display_name="Child Utterance Count",
        description="Number of utterances attributed to the CHI speaker.",
        value_type="integer",
        unit="utterances",
        calculation_method="Count of utterances where speaker == 'CHI'.",
        required_inputs=["utterances"],
        limitations=["Requires correct speaker diarization."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="adult_utterance_count",
        display_name="Adult Utterance Count",
        description="Number of utterances attributed to non-CHI, non-UNK speakers.",
        value_type="integer",
        unit="utterances",
        calculation_method="Count of utterances where speaker not in {CHI, UNK}.",
        required_inputs=["utterances"],
        limitations=["Requires correct speaker diarization."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="total_word_count",
        display_name="Total Word Count (Child)",
        description="Word tokens the CHI speaker produced, counted as CLAN's FREQ/KIDEVAL count them.",
        value_type="integer",
        unit="words",
        calculation_method=(
            "CLAN rules: retraced material ([/], [//], [///], [/-], [/?]), fillers and fragments (&...), "
            "omissions (0...), pauses and xxx/yyy/www are not words; [: target] replaces the word; "
            "(be)cause counts as because. Utterances with [+ exc] or www are left out. "
            "Thai is word-segmented with PyThaiNLP newmm. Uses %mor lemmas when the utterance has a %mor tier."
        ),
        required_inputs=["utterances"],
        limitations=["Thai word counts depend on the PyThaiNLP dictionary."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="number_of_different_words",
        display_name="Number of Different Words (NDW)",
        description="Different words in the CHI speaker's countable words (KIDEVAL FREQ_types).",
        value_type="integer",
        unit="words",
        calculation_method="Distinct lower-cased words among total_word_count tokens.",
        required_inputs=["utterances"],
        numerator_definition="Number of distinct token types",
        denominator_definition=None,
        limitations=[
            "Word forms, not lemmas, unless the transcript has a %mor tier.",
            "Grows with sample length; use ndw_100 to compare samples of different length.",
        ],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="type_token_ratio",
        display_name="Type–Token Ratio (TTR)",
        description="NDW divided by total word tokens (KIDEVAL FREQ_TTR).",
        value_type="ratio",
        unit="ratio",
        calculation_method="number_of_different_words / total_word_count",
        required_inputs=["utterances"],
        numerator_definition="number_of_different_words",
        denominator_definition="total_word_count",
        default_thresholds={"low": 0.4, "high": 0.8},
        limitations=["Falls as samples get longer; use mattr_50 or vocd_d to compare samples of different length."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mean_length_of_utterance_words",
        display_name="MLU (Words)",
        description="Mean words per CHI utterance, as CLAN's KIDEVAL MLU_Words.",
        value_type="float",
        unit="words per utterance",
        calculation_method=(
            "Countable words / MLU utterances. Utterances with xxx, yyy, www or [+ mlue] are left out "
            "entirely, utterances with no countable word are not utterances, and a '+,' line joins the "
            "interrupted utterance before it."
        ),
        required_inputs=["utterances"],
        numerator_definition="Countable words in MLU utterances",
        denominator_definition="mlu_utterance_count",
        limitations=["Word-based MLU; morpheme-based MLU requires a %mor tier."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="analyzable_utterance_count",
        display_name="Analysable Child Utterances",
        description="CHI utterances with at least one countable word (KIDEVAL Total_Utts).",
        value_type="integer",
        unit="utterances",
        calculation_method="CHI utterances with a countable word, without [+ exc] or www; '+,' continuations join the utterance before.",
        required_inputs=["utterances"],
        limitations=["KIDEVAL advises at least 50 utterances for DSS and IPSyn."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mlu_utterance_count",
        display_name="MLU Utterances",
        description="CHI utterances used for MLU (KIDEVAL MLU_Utts).",
        value_type="integer",
        unit="utterances",
        calculation_method="analyzable_utterance_count minus utterances with xxx, yyy, www or [+ mlue].",
        required_inputs=["utterances"],
        limitations=["Fewer than 50 utterances makes MLU less stable."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mlu_words_sd",
        display_name="MLU Standard Deviation",
        description="Standard deviation of utterance length in words, as CLAN's MLU reports it.",
        value_type="float",
        unit="words",
        calculation_method="sqrt(mean(length^2) - MLU^2) over MLU utterances; not defined for one utterance.",
        required_inputs=["utterances"],
        limitations=["Population standard deviation, as CLAN computes it."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mlu50_words",
        display_name="MLU50 (Words)",
        description="MLU over the first 50 MLU utterances (KIDEVAL MLU50_Words).",
        value_type="float",
        unit="words per utterance",
        calculation_method="Countable words / utterances over the first 50 MLU utterances.",
        required_inputs=["utterances"],
        limitations=["Equals MLU when the sample has 50 or fewer MLU utterances."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="ndw_100",
        display_name="NDW in First 100 Words",
        description="Different words in the first 100 word tokens (KIDEVAL NDW_100).",
        value_type="integer",
        unit="words",
        calculation_method="Distinct words among the first 100 countable tokens.",
        required_inputs=["utterances"],
        limitations=["Not computed when the child produced fewer than 100 words."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mattr_50",
        display_name=f"Moving-Average TTR ({MATTR_WINDOW} words)",
        description="Mean TTR of every 50-word window, as CLAN FREQ +b50 computes MATTR.",
        value_type="ratio",
        unit="ratio",
        calculation_method="Average over each window of 50 consecutive tokens of (different words / 50).",
        required_inputs=["utterances"],
        limitations=["Not computed when the child produced fewer than 50 words."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="vocd_d",
        display_name="VOCD D",
        description="Lexical diversity index D, computed with CLAN VOCD's method.",
        value_type="float",
        unit="D",
        calculation_method=(
            "For sample sizes 35-50, the mean TTR of 100 random samples without replacement; D is the "
            "least-squares fit of TTR = D/N (sqrt(1 + 2N/D) - 1), averaged over 3 trials. Seeded, so "
            "re-running gives the same value."
        ),
        required_inputs=["utterances"],
        limitations=[
            "Not computed with fewer than 50 words.",
            "Random sampling differs from CLAN's generator, so D can differ slightly from CLAN's.",
        ],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="coded_repetition_count",
        display_name="Coded Repetitions [/]",
        description="Repetitions the therapist marked with [/] (KIDEVAL repetition).",
        value_type="integer",
        unit="codes",
        calculation_method="Number of [/] codes in CHI utterances.",
        required_inputs=["utterances"],
        limitations=["Counts only what was coded in the transcript."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="retracing_count",
        display_name="Coded Retracings [//]",
        description="Self-corrections the therapist marked with [//] (KIDEVAL retracing).",
        value_type="integer",
        unit="codes",
        calculation_method="Number of [//] codes in CHI utterances.",
        required_inputs=["utterances"],
        limitations=["Counts only what was coded in the transcript."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="word_error_count",
        display_name="Coded Word Errors [*]",
        description="Word errors marked with [*] (KIDEVAL Word_Errors).",
        value_type="integer",
        unit="words",
        calculation_method="Each [*] counts once, or once per word when it follows an <...> group.",
        required_inputs=["utterances"],
        limitations=["Counts only what was coded in the transcript."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="thai_verbs_per_utterance",
        display_name="Thai Verbs per Utterance (experimental)",
        description="Verbs per Thai child MLU utterance, tagged by PyThaiNLP (Blackboard); a Thai counterpart of KIDEVAL Verbs_Utt.",
        value_type="float",
        unit="verbs per utterance",
        calculation_method="VV-tagged countable words / MLU utterances containing Thai. Thai adjectives are stative verbs and count.",
        required_inputs=["utterances"],
        limitations=[
            "Experimental: the tagger was trained on adult written Thai and is not validated on child speech.",
            "Not comparable with English Verbs_Utt norms.",
        ],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="thai_pronoun_count",
        display_name="Thai Pronouns (experimental)",
        description="Pronouns, including question words, in Thai child MLU utterances.",
        value_type="integer",
        unit="words",
        calculation_method="PR-tagged countable words (PyThaiNLP Blackboard tagger).",
        required_inputs=["utterances"],
        limitations=["Experimental: tagger not validated on child speech; kin terms used as pronouns (แม่, หนู) may be tagged as nouns."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="thai_particle_count",
        display_name="Thai Sentence-final Particles (experimental)",
        description="Sentence-final particles (ครับ, ค่ะ, นะ, จัง) in Thai child MLU utterances.",
        value_type="integer",
        unit="words",
        calculation_method="PA-tagged countable words (PyThaiNLP Blackboard tagger).",
        required_inputs=["utterances"],
        limitations=["Experimental: tagger not validated on child speech."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="thai_negator_count",
        display_name="Thai Negators (experimental)",
        description="Negators (ไม่) in Thai child MLU utterances.",
        value_type="integer",
        unit="words",
        calculation_method="NG-tagged countable words (PyThaiNLP Blackboard tagger).",
        required_inputs=["utterances"],
        limitations=["Experimental: tagger not validated on child speech."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="utterance_error_count",
        display_name="Coded Utterance Errors",
        description="Utterances with an error post-code (KIDEVAL Utt_Errors).",
        value_type="integer",
        unit="codes",
        calculation_method="Post-codes [+ *], [+ jar], [+ es], [+ cir], [+ per] and [+ gram] in CHI utterances.",
        required_inputs=["utterances"],
        limitations=["Counts only what was coded in the transcript."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mean_length_of_utterance_morphemes",
        display_name="MLU (Morphemes)",
        description="Mean number of morphemes per CHI utterance. Requires %mor dependent tier.",
        value_type="string",
        unit="morphemes",
        calculation_method="Not available — requires %mor tier.",
        required_inputs=["%mor dependent tier"],
        limitations=["Not computed by BasicFeatureProvider; requires CLAN/MOR."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="unintelligible_ratio",
        display_name="Unintelligible Utterance Ratio",
        description="Proportion of all utterances marked as unintelligible.",
        value_type="ratio",
        unit="ratio",
        calculation_method="count(unintelligible utterances) / total_utterance_count",
        required_inputs=["utterances"],
        numerator_definition="Utterances where unintelligible=True",
        denominator_definition="total_utterance_count",
        limitations=["Depends on accurate unintelligibility marking during review."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="unknown_speaker_ratio",
        display_name="Unknown Speaker Ratio",
        description="Proportion of utterances attributed to UNK speaker.",
        value_type="ratio",
        unit="ratio",
        calculation_method="count(speaker==UNK) / total_utterance_count",
        required_inputs=["utterances"],
        numerator_definition="Utterances where speaker == 'UNK'",
        denominator_definition="total_utterance_count",
        limitations=["High values indicate poor diarization; treat features with caution."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="question_ratio",
        display_name="Question Ratio (Child)",
        description="Proportion of CHI utterances containing a '?' character.",
        value_type="ratio",
        unit="ratio",
        calculation_method="count(CHI utterances with '?') / child_utterance_count",
        required_inputs=["utterances"],
        numerator_definition="CHI utterances containing '?'",
        denominator_definition="child_utterance_count",
        limitations=["Punctuation-based heuristic only."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="repetition_marker_count",
        display_name="Repetition Marker Count",
        description="Count of CHAT retracing markers [/] or immediate word repetitions in CHI utterances.",
        value_type="integer",
        unit="markers",
        calculation_method=(
            "Per CHI utterance: immediate repeats of one to three tokens (Thai text is "
            "word-segmented first, so ไปไป and ไป โรงเรียน ไป โรงเรียน count), or the number "
            "of [/] markers if larger, plus [//] reformulation markers."
        ),
        required_inputs=["utterances"],
        limitations=["Heuristic; misses repetitions across utterances and repeats longer than three tokens."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="child_response_count",
        display_name="Child Responses to Adults",
        description="Adult utterances directly followed by a child utterance: the child taking up a turn.",
        value_type="integer",
        unit="turns",
        calculation_method=(
            "Count of adjacent (adult line, CHI line) pairs in transcript order; UNK lines are skipped. "
            "Like LENA's adult-child conversational turn count, on transcript lines."
        ),
        required_inputs=["utterances"],
        limitations=[
            "Counts adjacency only; whether the child's line answers the adult needs the therapist.",
            "Depends on correct speaker labels.",
        ],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="child_response_rate",
        display_name="Child Response Rate",
        description="Share of adult utterances directly followed by a child utterance.",
        value_type="ratio",
        unit="ratio",
        calculation_method="child_response_count / adult utterances (UNK lines skipped).",
        required_inputs=["utterances"],
        limitations=["Lower when the adult says several lines in a row, as in story telling."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="mlt_ratio",
        display_name="Turn Length Ratio (child / adult)",
        description="The child's mean words per turn over the adults' (MLT ratio, Assaf et al. 2025).",
        value_type="ratio",
        unit="ratio",
        calculation_method=(
            "A turn is a run of consecutive lines by the child or by the adults; words are counted "
            "with CLAN's rules on every speaker's lines."
        ),
        required_inputs=["utterances"],
        limitations=["Depends on how much the adult talks as well as on the child."],
        clinical_interpretation_caution=_CAUTION,
    ),
    FeatureDefinition(
        feature_name="pronoun_reversal_cue_count",
        display_name="Pronoun Reversal Cue Count",
        description="Review cue count for atypical pronoun usage patterns in CHI utterances.",
        value_type="integer",
        unit="review cues",
        calculation_method=(
            "English: regex match for patterns like 'you am', 'me am', 'my want', 'i are'. "
            "Thai: CHI utterances where a second-person pronoun is followed by a desire or "
            "state verb (for example เธออยาก), counted once per utterance."
        ),
        required_inputs=["utterances"],
        limitations=[
            "Simple heuristic; high false-negative rate. Review cue only.",
            "Thai children often refer to themselves by name or kin term; that is not flagged.",
        ],
        clinical_interpretation_caution="Review cue only; not diagnostic. Therapist context required.",
    ),
    FeatureDefinition(
        feature_name="echolalia_cue_count",
        display_name="Echolalia Cue Count",
        description="Count of CHI utterances that immediately echo the preceding adult utterance.",
        value_type="integer",
        unit="review cues",
        calculation_method=(
            "English: CHI utterances that match the preceding non-CHI utterance (lowercased, stripped). "
            "Thai: a CHI utterance directly after an adult utterance that repeats it verbatim, "
            "with or without a polite particle, or repeats most of its words."
        ),
        required_inputs=["utterances"],
        limitations=[
            "Detects only immediate echoes; delayed echolalia not captured.",
            "A natural answer that reuses the adult's words can be flagged; check each one in context.",
        ],
        clinical_interpretation_caution="Review cue only; therapist context required.",
    ),
    FeatureDefinition(
        feature_name="limited_reciprocal_question_cue",
        display_name="Limited Reciprocal Question Cue",
        description="Boolean flag: True if the child produced no questions and at least 3 utterances.",
        value_type="boolean",
        unit="boolean",
        calculation_method="question_ratio == 0 AND child_utterance_count >= 3",
        required_inputs=["utterances"],
        limitations=["Coarse flag; short samples may produce false positives."],
        clinical_interpretation_caution="Review cue only; not diagnostic.",
    ),
    FeatureDefinition(
        feature_name="repetitive_phrase_cue",
        display_name="Repetitive Phrase Cue Count",
        description="Count of immediate word-pair repetitions within CHI utterances.",
        value_type="integer",
        unit="review cues",
        calculation_method="Immediate repeats of a single token in CHI utterances; Thai text is word-segmented first.",
        required_inputs=["utterances"],
        limitations=["Only captures adjacent single-word repetitions."],
        clinical_interpretation_caution="Review cue only; not diagnostic.",
    ),
    FeatureDefinition(
        feature_name="atypical_response_cue",
        display_name="Atypical Response Cue",
        description="Placeholder for manual therapist annotation of atypical responses.",
        value_type="string",
        unit="review status",
        calculation_method="Not automated; always returns 'needs_context'.",
        required_inputs=["therapist_review"],
        limitations=["Cannot be computed automatically from transcripts alone."],
        clinical_interpretation_caution="Requires therapist qualitative assessment.",
    ),
]


def _with_child_analyses(all_utts, child_analyses):
    """(utterance, side, analysis) in transcript order, reusing the child lines' analyses."""
    remaining = iter(child_analyses)
    for utterance in all_utts:
        side = speaker_side(utterance.speaker)
        analysis = next(remaining) if str(utterance.speaker).upper() == "CHI" else None
        yield utterance, side, analysis


# ---------------------------------------------------------------------------
# BasicFeatureProvider
# ---------------------------------------------------------------------------

class BasicFeatureProvider(BaseFeatureProvider):
    """
    Rule-based feature provider requiring only the utterance list.

    No external binaries needed → always available.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def provider_id(self) -> str:
        return _PROVIDER_ID

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    @property
    def provider_version(self) -> str:
        return _PROVIDER_VERSION

    @property
    def feature_schema_version(self) -> str:
        return _SCHEMA_VERSION

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_provider_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "feature_schema_version": self.feature_schema_version,
            "description": (
                "Rule-based language sample feature provider. "
                "Computes descriptive linguistic features from CHAT-parsed "
                "transcripts using utterance text and speaker labels only."
            ),
            "required_inputs": ["Transcript.utterances"],
            "external_dependencies": [],
            "limitations": [
                "Does not support morpheme-based MLU (requires %mor tier / CLAN).",
                "All features are descriptive; none are diagnostic.",
                "Atypical-response cue cannot be automated.",
            ],
            "feature_count": len(_DEFINITIONS),
            "available": True,
        }

    def check_availability(self) -> ProviderAvailability:
        # BasicFeatureProvider has no external dependencies.
        return ProviderAvailability(available=True, reason="No external dependencies.")

    def get_feature_definitions(self) -> list[FeatureDefinition]:
        return [d.model_copy(update={"feature_version": _SCHEMA_VERSION}) for d in _DEFINITIONS]

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def extract_features(
        self,
        transcript: Transcript,
        config: dict | None = None,
    ) -> FeatureExtractionResult:
        cfg = config or {}
        now = datetime.now(timezone.utc)
        warnings: list[str] = []

        # ---- Partition utterances ----------------------------------------
        all_utts = transcript.utterances
        child = [u for u in all_utts if str(u.speaker).upper() == "CHI"]
        adult = [u for u in all_utts if str(u.speaker).upper() not in {"CHI", "UNK"}]
        unk_count = sum(1 for u in all_utts if str(u.speaker).upper() == "UNK")

        # ---- Insufficient data guard -------------------------------------
        insufficient = len(child) < _MIN_CHILD_UTTS
        if insufficient:
            warnings.append(
                f"Fewer than {_MIN_CHILD_UTTS} child utterances found "
                f"({len(child)}). Feature reliability is reduced."
            )

        # ---- Count words and utterances with CLAN's rules ------------------
        analyses = [analyze_main_tier(u.text) for u in child]
        measures = compute_language_sample_measures(analyses, [_mor_tier(u) for u in child])
        # Repetition cues look at everything said, retraced words included.
        child_token_lists = [list(a.spoken_words) for a in analyses]
        if measures.mlu_utterances < RECOMMENDED_UTTERANCES:
            warnings.append(
                f"Only {measures.mlu_utterances} child utterances count towards MLU; "
                f"CLAN's KIDEVAL uses at least {RECOMMENDED_UTTERANCES} for DSS and IPSyn."
            )

        # ---- Denominators (guard against zero division) ----------------------
        total_utts = len(all_utts) or 1
        child_count = len(child) or 1  # used only in ratio denominators

        # ---- UNK speaker warning --------------------------------------------
        unk_ratio = unk_count / total_utts
        if unk_ratio > 0.2:
            warnings.append(
                f"High unknown-speaker ratio ({unk_ratio:.0%}). "
                "Speaker diarization may be unreliable."
            )

        # None means "not computed", which is different from "none found".
        pronoun_evidence = _pronoun_cue_evidence(child)
        pronoun_cues = None if pronoun_evidence is None else sum(count for _, count in pronoun_evidence)
        echolalia_pairs = _echolalia_pairs(all_utts)
        turns = turn_taking(
            (speaker_side(u.speaker), len(analysis.words) if side == "CHI" else len(analyze_main_tier(u.text).words))
            for u, side, analysis in _with_child_analyses(all_utts, analyses)
        )

        # ---- Build FeatureValue list ----------------------------------------
        def fv(
            name: str,
            value: float | int | str | bool | None,
            *,
            unit: str = "count",
            value_type: str = "count",
            numerator: float | int | None = None,
            denominator: float | int | None = None,
            insufficient_data: bool = False,
            hint: str = "Descriptive language sample value; therapist interpretation required.",
            extra_warnings: list[str] | None = None,
            evidence: list[dict[str, str]] | None = None,
        ) -> FeatureValue:
            return FeatureValue(
                name=name,
                value=value,
                unit=unit,
                value_type=value_type,
                numerator=numerator,
                denominator=denominator,
                provider_name=_PROVIDER_NAME,
                feature_version=_SCHEMA_VERSION,
                transcript_id=transcript.transcript_id,
                session_id=transcript.session_id,
                computed_at=now,
                insufficient_data=insufficient_data or insufficient,
                interpretation_hint=hint,
                warnings=extra_warnings or [],
                evidence=evidence or [],
            )

        values: list[FeatureValue] = [
            fv("total_utterance_count", len(all_utts), unit="utterances", value_type="integer"),
            fv("child_utterance_count", len(child), unit="utterances", value_type="integer"),
            fv("adult_utterance_count", len(adult), unit="utterances", value_type="integer"),
            fv(
                "total_word_count",
                measures.freq_tokens,
                unit="words",
                value_type="integer",
            ),
            fv(
                "number_of_different_words",
                measures.freq_types,
                unit="words",
                value_type="integer",
            ),
            fv(
                "type_token_ratio",
                measures.ttr if measures.ttr is not None else 0,
                unit="ratio",
                value_type="ratio",
                numerator=measures.freq_types,
                denominator=measures.freq_tokens,
            ),
            fv(
                "mean_length_of_utterance_words",
                measures.mlu_words if measures.mlu_words is not None else 0,
                unit="words per utterance",
                value_type="float",
                numerator=measures.mlu_word_total,
                denominator=measures.mlu_utterances,
            ),
            fv("analyzable_utterance_count", measures.total_utterances, unit="utterances", value_type="integer"),
            fv("mlu_utterance_count", measures.mlu_utterances, unit="utterances", value_type="integer"),
            _optional(fv, "mlu_words_sd", measures.mlu_words_sd, "words", "float",
                      "Needs at least two MLU utterances."),
            _optional(fv, "mlu50_words", measures.mlu50_words, "words per utterance", "float",
                      "No MLU utterances."),
            _optional(fv, "ndw_100", measures.ndw_100, "words", "integer",
                      "Needs at least 100 child words."),
            _optional(fv, "mattr_50", measures.mattr, "ratio", "ratio",
                      f"Needs at least {MATTR_WINDOW} child words."),
            _optional(fv, "vocd_d", measures.vocd_d, "D", "float",
                      "Needs at least 50 child words."),
            fv("coded_repetition_count", measures.repetitions, unit="codes", value_type="integer"),
            fv("retracing_count", measures.retracings, unit="codes", value_type="integer"),
            fv("word_error_count", measures.word_errors, unit="words", value_type="integer"),
            fv("utterance_error_count", measures.utterance_errors, unit="codes", value_type="integer"),
            *_thai_pos_values(fv, thai_pos_counts(analyses)),
            fv(
                "mean_length_of_utterance_morphemes",
                "not_available",
                unit="morphemes",
                value_type="string",
                insufficient_data=True,
                hint="Morpheme-based MLU requires %mor tier (CLAN). Not computed by BasicFeatureProvider.",
                extra_warnings=["MLU-morphemes requires %mor dependent tier; not available."],
            ),
            fv(
                "unintelligible_ratio",
                round(
                    sum(1 for u in all_utts if u.unintelligible) / total_utts, 4
                ),
                unit="ratio",
                value_type="ratio",
                numerator=sum(1 for u in all_utts if u.unintelligible),
                denominator=total_utts,
            ),
            fv(
                "unknown_speaker_ratio",
                round(unk_count / total_utts, 4),
                unit="ratio",
                value_type="ratio",
                numerator=unk_count,
                denominator=total_utts,
            ),
            fv(
                "question_ratio",
                round(
                    sum(1 for u in child if "?" in u.text) / child_count, 4
                ) if child else 0,
                unit="ratio",
                value_type="ratio",
                numerator=sum(1 for u in child if "?" in u.text),
                denominator=len(child) if child else 0,
            ),
            fv(
                "repetition_marker_count",
                sum(
                    _repetition_marker_count(u.text, tokens)
                    for u, tokens in zip(child, child_token_lists)
                ),
                unit="markers",
                value_type="integer",
                hint="Review cue only; not diagnostic.",
            ),
            fv("child_response_count", turns.child_responses, unit="turns", value_type="integer",
               numerator=turns.child_responses, denominator=turns.adult_utterances),
            _optional(fv, "child_response_rate",
                      None if turns.child_response_rate is None else round(turns.child_response_rate, 4),
                      "ratio", "ratio", "No adult utterances."),
            _optional(fv, "mlt_ratio", None if turns.mlt_ratio is None else round(turns.mlt_ratio, 4),
                      "ratio", "ratio", "Needs words from both the child and an adult."),
            fv(
                "pronoun_reversal_cue_count",
                pronoun_cues,
                unit="review cues",
                value_type="integer",
                hint="Review cue only; not diagnostic. Therapist context required.",
                extra_warnings=(
                    ["Thai pronoun cues could not be computed; the Thai language module is unavailable."]
                    if pronoun_cues is None
                    else None
                ),
                evidence=[{"child_utterance_id": utterance_id} for utterance_id, _ in pronoun_evidence or []],
            ),
            fv(
                "echolalia_cue_count",
                len(echolalia_pairs),
                unit="review cues",
                value_type="integer",
                hint="Review cue only; therapist context required.",
                evidence=echolalia_pairs,
            ),
            fv(
                "limited_reciprocal_question_cue",
                sum(1 for u in child if "?" in u.text) == 0 and len(child) >= _MIN_CHILD_UTTS,
                unit="boolean",
                value_type="boolean",
                hint="Review cue only; not diagnostic.",
            ),
            fv(
                "repetitive_phrase_cue",
                sum(_repeated_ngrams(tokens, max_n=1) for tokens in child_token_lists),
                unit="review cues",
                value_type="integer",
                hint="Review cue only; not diagnostic.",
            ),
            fv(
                "atypical_response_cue",
                "needs_context",
                unit="review status",
                value_type="string",
                hint="Cannot be automated. Requires therapist qualitative assessment.",
                extra_warnings=["atypical_response_cue cannot be computed automatically."],
            ),
        ]

        return FeatureExtractionResult(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            feature_schema_version=self.feature_schema_version,
            tokenizer_version=None,
            transcript_id=transcript.transcript_id,
            session_id=transcript.session_id,
            computed_at=now,
            values=values,
            warnings=warnings,
            insufficient_data=insufficient,
            valid=True,
            config_used=cfg,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mor_tier(utterance: Utterance) -> str | None:
    """The utterance's %mor tier text, when the transcript has one."""
    for tier in utterance.dependent_tiers:
        if tier.tier.lstrip("%").lower() == "mor":
            return tier.raw_text
    return None


def _thai_pos_values(fv, counts: ThaiPosCounts | None) -> list[FeatureValue]:
    """Experimental Thai word-class values; not computed without Thai child speech or the tagger."""
    reason = "Needs Thai child utterances and PyThaiNLP's Blackboard tagger."
    note = "Experimental: Thai POS tagger not validated on child speech."
    rows = [
        ("thai_verbs_per_utterance", counts.verbs_per_utterance if counts else None, "verbs per utterance", "float"),
        ("thai_pronoun_count", counts.pronouns if counts else None, "words", "integer"),
        ("thai_particle_count", counts.particles if counts else None, "words", "integer"),
        ("thai_negator_count", counts.negators if counts else None, "words", "integer"),
    ]
    values = []
    for name, value, unit, value_type in rows:
        item = _optional(fv, name, value, unit, value_type, reason)
        if value is not None:
            item.warnings.append(note)
        values.append(item)
    return values


def _optional(fv, name: str, value, unit: str, value_type: str, missing_reason: str) -> FeatureValue:
    """A measure that needs a minimum sample; None with a warning when it is too short."""
    if value is None:
        return fv(name, None, unit=unit, value_type=value_type, insufficient_data=True,
                  extra_warnings=[f"Not computed: {missing_reason}"])
    return fv(name, value, unit=unit, value_type=value_type)


_THAI_CHARS = re.compile(r"[\u0e00-\u0e7f]")
_WORD_TOKEN = re.compile(r"[\w\u0e00-\u0e7f]")


def _repeated_ngrams(tokens: Sequence[str], *, max_n: int = 3) -> int:
    """
    Count immediate repeats of one to ``max_n`` tokens, longest match first.

    Follows Batchalign's n-gram retrace detection: ``a a b`` is one repeat,
    ``a b a b c`` is one repeat of ``a b``, and ``a a a`` is two.
    """
    words = [tok for tok in tokens if _WORD_TOKEN.search(tok)]
    repeats = 0
    index = 0
    while index < len(words):
        for size in range(max_n, 0, -1):
            if words[index:index + size] == words[index + size:index + 2 * size]:
                repeats += 1
                index += size
                break
        else:
            index += 1
    return repeats


def _repetition_marker_count(text: str, tokens: Sequence[str]) -> int:
    """Repetition events in one utterance, from coding or from the words."""
    # A coded repeat ("I [/] I want") also shows up as a token repeat, so the
    # two sources describe the same events: take whichever finds more.
    retraces = max(len(re.findall(r"\[/\]", text)), _repeated_ngrams(tokens))
    return retraces + len(re.findall(r"\[//\]", text))


def _thai_lsa():
    """Thai language-sample helpers, or None when the research package is absent."""
    try:
        from src.clinical_speech import thai_lsa
    except Exception:
        return None
    return thai_lsa


def _pronoun_cue(text: str) -> int | None:
    """Atypical pronoun-use cues in one utterance; None if it cannot be assessed."""
    if _THAI_CHARS.search(text):
        thai = _thai_lsa()
        if thai is None:
            return None
        return 1 if thai.detect_thai_pronoun_reversal(text, thai.tokenize_thai_words(text)) else 0
    return len(re.findall(r"\b(?:you am|me am|my want|i are)\b", text, re.I))


def _pronoun_cue_evidence(child: Sequence[Utterance]) -> list[tuple[str, int]] | None:
    """(utterance id, cue count) for each flagged child utterance; None if not computable."""
    flagged: list[tuple[str, int]] = []
    for utterance in child:
        cues = _pronoun_cue(utterance.text)
        if cues is None:
            return None
        if cues:
            flagged.append((utterance.utterance_id, cues))
    return flagged


def _echolalia_pairs(utterances: Sequence[Utterance]) -> list[dict[str, str]]:
    """
    Adult/child utterance pairs where the child echoes the preceding adult turn.

    English keeps the verbatim rule (lowercased, whitespace-stripped). Thai
    uses the shared Thai rule, which also accepts an added polite particle or
    a mostly repeated utterance, and only looks at the directly preceding turn.
    """
    thai = _thai_lsa()
    pairs: list[dict[str, str]] = []
    previous_adult: Utterance | None = None
    previous_was_adult = False
    for utt in utterances:
        speaker = str(utt.speaker).upper()
        if speaker != "CHI":
            previous_adult = utt
            previous_was_adult = True
            continue
        category = None
        if previous_adult is not None:
            adult_text = previous_adult.text.strip().lower()
            if thai is not None and _THAI_CHARS.search(utt.text):
                if previous_was_adult:
                    category = thai.detect_echolalia(adult_text, utt.text)[0]
            elif adult_text and utt.text.strip().lower() == adult_text:
                category = "immediate_verbatim"
        if category and previous_adult is not None:
            pairs.append({
                "adult_utterance_id": previous_adult.utterance_id,
                "child_utterance_id": utt.utterance_id,
                "category": category,
            })
        previous_was_adult = False
    return pairs
