"""Legacy non-speech word count, including expected rejected inputs.

The caller determines which samples are non-speech. This preserves the legacy
report's scope; a stricter research definition belongs to a new profile.
"""

from app.stt_benchmark.text.normalization import normalized_words


def non_speech_word_count(hypothesis: str) -> int:
    return len(normalized_words(hypothesis))
