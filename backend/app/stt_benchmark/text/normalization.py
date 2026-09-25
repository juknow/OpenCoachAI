import re
import unicodedata

WORD_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*")
FILLER_WORDS = frozenset({"um", "uh", "er", "ah", "hmm"})


def normalized_words(text: str) -> list[str]:
    """Return comparable English word tokens without hiding speech errors."""
    normalized = unicodedata.normalize("NFKC", text).lower().replace("’", "'")
    return WORD_PATTERN.findall(normalized)
