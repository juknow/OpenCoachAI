from dataclasses import dataclass

from app.stt_benchmark.text.normalization import normalized_words


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
