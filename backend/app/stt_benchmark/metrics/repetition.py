from collections import Counter

from app.stt_benchmark.text.normalization import normalized_words

from .counts import RetentionBreakdown, retention_breakdown


def adjacent_repetition_retention(reference: str, hypothesis: str) -> RetentionBreakdown:
    return retention_breakdown(
        _adjacent_repetition_counts(normalized_words(reference)),
        _adjacent_repetition_counts(normalized_words(hypothesis)),
    )


def _adjacent_repetition_counts(tokens: list[str]) -> Counter[str]:
    return Counter(
        token for index, token in enumerate(tokens[1:], start=1) if token == tokens[index - 1]
    )
