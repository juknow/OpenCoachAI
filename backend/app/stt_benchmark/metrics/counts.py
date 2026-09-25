from collections import Counter
from dataclasses import dataclass


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


def retention_breakdown(
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
