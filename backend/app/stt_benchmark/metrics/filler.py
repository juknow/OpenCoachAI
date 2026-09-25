from collections import Counter

from app.stt_benchmark.text.normalization import FILLER_WORDS, normalized_words

from .counts import RetentionBreakdown, retention_breakdown


def filler_retention(reference: str, hypothesis: str) -> RetentionBreakdown:
    reference_fillers = Counter(
        token for token in normalized_words(reference) if token in FILLER_WORDS
    )
    hypothesis_fillers = Counter(
        token for token in normalized_words(hypothesis) if token in FILLER_WORDS
    )
    return retention_breakdown(reference_fillers, hypothesis_fillers)
