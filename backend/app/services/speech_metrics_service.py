import re
from collections import Counter

from app.providers.base import ProviderTranscription, ProviderWord
from app.schemas.evaluation import SpeechMetrics

WORD_PATTERN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")
FILLERS = {"um", "uh", "er", "ah", "hmm"}
FUNCTIONAL_MARKERS = (
    "well",
    "honestly",
    "let me think",
    "you know",
    "i mean",
    "first of all",
    "for example",
    "because",
    "however",
    "so",
)


def _word_counts(values: list[str]) -> list[dict[str, object]]:
    return [{"word": word, "count": count} for word, count in Counter(values).items()]


def _phrase_count(text: str, phrase: str) -> int:
    return len(re.findall(rf"\b{re.escape(phrase)}\b", text, flags=re.IGNORECASE))


def _repetitions(words: list[str]) -> tuple[list[str], int]:
    repeated: list[str] = []
    repeated_word_count = 0
    for index in range(1, len(words)):
        if words[index] == words[index - 1]:
            repeated_word_count += 1
            if words[index] not in repeated:
                repeated.append(words[index])
    for size in (2, 3):
        for index in range(size, len(words) - size + 1):
            if words[index - size : index] == words[index : index + size]:
                phrase = " ".join(words[index : index + size])
                if phrase not in repeated:
                    repeated.append(phrase)
    return repeated[:5], repeated_word_count


def _pause_metrics(
    words: tuple[ProviderWord, ...], duration_seconds: float
) -> tuple[float, list[float], list[float], float]:
    if not words:
        return 0.0, [], [], 0.0
    ordered = sorted(words, key=lambda item: (item.start, item.end))
    initial_delay = min(duration_seconds, max(0.0, ordered[0].start))
    short_pauses: list[float] = []
    long_pauses: list[float] = []
    silence = initial_delay
    previous_end = ordered[0].end
    for word in ordered[1:]:
        gap = max(0.0, word.start - previous_end)
        silence += gap
        if 0.28 <= gap <= 0.9:
            short_pauses.append(gap)
        elif gap > 0.9:
            long_pauses.append(gap)
        previous_end = max(previous_end, word.end)
    silence += max(0.0, duration_seconds - previous_end)
    ratio = min(100.0, (silence / max(duration_seconds, 0.001)) * 100)
    return initial_delay, short_pauses, long_pauses, ratio


def calculate_speech_metrics(
    transcription: ProviderTranscription,
    duration_seconds: float,
) -> SpeechMetrics:
    text = transcription.text
    original_words = WORD_PATTERN.findall(text)
    words = [word.lower() for word in original_words]
    word_count = len(words)
    sentence_count = len(
        [value for value in SENTENCE_PATTERN.findall(text.strip()) if value.strip()]
    )
    fillers = [word for word in words if word in FILLERS]
    repetitions, repeated_word_count = _repetitions(words)
    markers = [
        {"word": marker, "count": count}
        for marker in FUNCTIONAL_MARKERS
        if (count := _phrase_count(text, marker))
    ]
    opening = " ".join(
        word.text.strip()
        for word in transcription.words
        if word.start <= 20 and word.text.strip()
    )
    if not opening:
        opening_limit = max(1, round((word_count / max(duration_seconds, 1)) * 20))
        opening = " ".join(original_words[:opening_limit])
    initial, short_pauses, long_pauses, silence_ratio = _pause_metrics(
        transcription.words, duration_seconds
    )
    average_short = sum(short_pauses) / len(short_pauses) if short_pauses else 0.0
    average_long = sum(long_pauses) / len(long_pauses) if long_pauses else 0.0
    return SpeechMetrics.model_validate(
        {
            "durationSeconds": duration_seconds,
            "wordCount": word_count,
            "wordsPerMinute": round(word_count / max(duration_seconds / 60, 1 / 60)),
            "fillerWords": _word_counts(fillers),
            "repeatedPhrases": repetitions,
            "functionalDiscourseMarkers": markers,
            "fillerRatePer100Words": round((len(fillers) / max(word_count, 1)) * 100, 1),
            "opening20SecondEstimate": opening[:3000],
            "acoustic": {
                "initialResponseDelaySeconds": initial,
                "hesitationPauseCount": len(short_pauses),
                "averageHesitationPauseSeconds": round(average_short, 3),
                "longPauseCount": len(long_pauses),
                "averageLongPauseSeconds": round(average_long, 3),
                "silenceRatio": round(silence_ratio, 1),
                "energyVariationIndex": 0,
                "confidence": "medium" if transcription.words else "low",
            },
            "sentenceCount": sentence_count,
            "averageSentenceLength": round(word_count / max(sentence_count, 1), 1),
            "repeatedWordRatio": round((repeated_word_count / max(word_count, 1)) * 100, 1),
        }
    )
