import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

WORD_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")
FILLER_WORDS = frozenset({"um", "uh", "er", "ah", "hmm"})


def normalized_words(text: str) -> list[str]:
    """Return comparable English word tokens without hiding speech errors."""
    normalized = unicodedata.normalize("NFKC", text).lower().replace("’", "'")
    return WORD_PATTERN.findall(normalized)


@dataclass(frozen=True)
class WordErrorBreakdown:
    reference_words: int
    hypothesis_words: int
    substitutions: int
    deletions: int
    insertions: int

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def word_error_rate(self) -> float:
        if self.reference_words == 0 and self.hypothesis_words == 0:
            return 0.0
        return self.errors / max(1, self.reference_words)


@dataclass(frozen=True)
class RetentionBreakdown:
    reference_items: int
    hypothesis_items: int
    matched_items: int

    @property
    def recall(self) -> float | None:
        if self.reference_items == 0:
            return None
        return self.matched_items / self.reference_items

    @property
    def precision(self) -> float | None:
        if self.hypothesis_items == 0:
            return None
        return self.matched_items / self.hypothesis_items


def word_error_breakdown(reference: str, hypothesis: str) -> WordErrorBreakdown:
    """Calculate deterministic Levenshtein word errors for two transcripts."""
    reference_tokens = normalized_words(reference)
    hypothesis_tokens = normalized_words(hypothesis)
    reference_count = len(reference_tokens)
    hypothesis_count = len(hypothesis_tokens)

    distances = [list(range(hypothesis_count + 1))]
    for reference_index in range(1, reference_count + 1):
        row = [reference_index] + [0] * hypothesis_count
        distances.append(row)
        for hypothesis_index in range(1, hypothesis_count + 1):
            if reference_tokens[reference_index - 1] == hypothesis_tokens[hypothesis_index - 1]:
                row[hypothesis_index] = distances[reference_index - 1][hypothesis_index - 1]
                continue
            row[hypothesis_index] = 1 + min(
                distances[reference_index - 1][hypothesis_index - 1],
                distances[reference_index - 1][hypothesis_index],
                row[hypothesis_index - 1],
            )

    substitutions = 0
    deletions = 0
    insertions = 0
    reference_index = reference_count
    hypothesis_index = hypothesis_count

    while reference_index > 0 or hypothesis_index > 0:
        if (
            reference_index > 0
            and hypothesis_index > 0
            and reference_tokens[reference_index - 1] == hypothesis_tokens[hypothesis_index - 1]
            and distances[reference_index][hypothesis_index]
            == distances[reference_index - 1][hypothesis_index - 1]
        ):
            reference_index -= 1
            hypothesis_index -= 1
            continue

        if (
            reference_index > 0
            and hypothesis_index > 0
            and distances[reference_index][hypothesis_index]
            == distances[reference_index - 1][hypothesis_index - 1] + 1
        ):
            substitutions += 1
            reference_index -= 1
            hypothesis_index -= 1
            continue

        if (
            reference_index > 0
            and distances[reference_index][hypothesis_index]
            == distances[reference_index - 1][hypothesis_index] + 1
        ):
            deletions += 1
            reference_index -= 1
            continue

        insertions += 1
        hypothesis_index -= 1

    return WordErrorBreakdown(
        reference_words=reference_count,
        hypothesis_words=hypothesis_count,
        substitutions=substitutions,
        deletions=deletions,
        insertions=insertions,
    )


def filler_retention(reference: str, hypothesis: str) -> RetentionBreakdown:
    reference_fillers = Counter(
        token for token in normalized_words(reference) if token in FILLER_WORDS
    )
    hypothesis_fillers = Counter(
        token for token in normalized_words(hypothesis) if token in FILLER_WORDS
    )
    return _retention_breakdown(reference_fillers, hypothesis_fillers)


def adjacent_repetition_retention(reference: str, hypothesis: str) -> RetentionBreakdown:
    return _retention_breakdown(
        _adjacent_repetition_counts(normalized_words(reference)),
        _adjacent_repetition_counts(normalized_words(hypothesis)),
    )


def _adjacent_repetition_counts(tokens: list[str]) -> Counter[str]:
    return Counter(
        token
        for index, token in enumerate(tokens[1:], start=1)
        if token == tokens[index - 1]
    )


def _retention_breakdown(
    reference_counts: Counter[str],
    hypothesis_counts: Counter[str],
) -> RetentionBreakdown:
    matched_items = sum(
        min(reference_count, hypothesis_counts[item])
        for item, reference_count in reference_counts.items()
    )
    return RetentionBreakdown(
        reference_items=sum(reference_counts.values()),
        hypothesis_items=sum(hypothesis_counts.values()),
        matched_items=matched_items,
    )
