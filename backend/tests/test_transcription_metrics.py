import pytest

from app.evals.transcription_metrics import (
    adjacent_repetition_retention,
    filler_retention,
    normalized_words,
    word_error_breakdown,
)


def test_normalization_ignores_case_and_punctuation_without_removing_fillers() -> None:
    assert normalized_words("Um, I'M here... uh!") == ["um", "i'm", "here", "uh"]


def test_identical_transcripts_have_zero_word_error_rate() -> None:
    result = word_error_breakdown(
        "Um, I I went there yesterday.",
        "um i i went there yesterday",
    )

    assert result.errors == 0
    assert result.word_error_rate == 0
    assert result.reference_words == 6
    assert result.hypothesis_words == 6


def test_word_error_breakdown_counts_substitution() -> None:
    result = word_error_breakdown(
        "I really like this park",
        "I truly like this park",
    )

    assert result.substitutions == 1
    assert result.deletions == 0
    assert result.insertions == 0
    assert result.word_error_rate == pytest.approx(1 / 5)


def test_word_error_breakdown_counts_insertion() -> None:
    result = word_error_breakdown("I like this park", "I really like this park")

    assert result.insertions == 1
    assert result.substitutions == 0
    assert result.deletions == 0


def test_missing_repeated_word_counts_as_deletion() -> None:
    result = word_error_breakdown("I I went home", "I went home")

    assert result.deletions == 1
    assert result.substitutions == 0
    assert result.insertions == 0


@pytest.mark.parametrize(
    ("reference", "hypothesis", "expected_rate"),
    [
        ("", "", 0.0),
        ("", "invented words", 2.0),
        ("spoken words", "", 1.0),
    ],
)
def test_empty_transcript_edges_have_defined_word_error_rate(
    reference: str,
    hypothesis: str,
    expected_rate: float,
) -> None:
    assert word_error_breakdown(reference, hypothesis).word_error_rate == expected_rate


def test_filler_retention_counts_preserved_and_missing_fillers() -> None:
    result = filler_retention(
        "Um, I went there, uh, yesterday.",
        "Um, I went there yesterday.",
    )

    assert result.reference_items == 2
    assert result.hypothesis_items == 1
    assert result.matched_items == 1
    assert result.recall == pytest.approx(0.5)
    assert result.precision == pytest.approx(1.0)


def test_filler_precision_exposes_fillers_added_by_stt() -> None:
    result = filler_retention("Um, I went there.", "Um, uh, I went there.")

    assert result.recall == pytest.approx(1.0)
    assert result.precision == pytest.approx(0.5)


def test_retention_is_not_applicable_when_reference_has_no_fillers() -> None:
    result = filler_retention("I went there.", "Uh, I went there.")

    assert result.recall is None
    assert result.precision == pytest.approx(0.0)


def test_adjacent_repetition_retention_counts_each_extra_word() -> None:
    result = adjacent_repetition_retention("I I I went home.", "I I went home.")

    assert result.reference_items == 2
    assert result.hypothesis_items == 1
    assert result.matched_items == 1
    assert result.recall == pytest.approx(0.5)
    assert result.precision == pytest.approx(1.0)


def test_different_repeated_word_is_not_a_preserved_repetition() -> None:
    result = adjacent_repetition_retention("I I went home.", "I went went home.")

    assert result.matched_items == 0
    assert result.recall == pytest.approx(0.0)
    assert result.precision == pytest.approx(0.0)
