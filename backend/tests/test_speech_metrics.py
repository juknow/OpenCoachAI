from app.providers.base import ProviderTranscription, ProviderWord
from app.services.speech_metrics_service import calculate_speech_metrics


def test_speech_metrics_are_deterministic_from_transcript_and_timestamps() -> None:
    transcription = ProviderTranscription(
        text="Um, I I went home. However, I felt happy.",
        model="base.en",
        words=(
            ProviderWord("Um", 0.5, 0.7),
            ProviderWord("I", 0.8, 0.9),
            ProviderWord("I", 1.0, 1.1),
            ProviderWord("went", 2.2, 2.5),
            ProviderWord("home", 2.6, 2.9),
            ProviderWord("However", 4.0, 4.4),
            ProviderWord("I", 4.5, 4.6),
            ProviderWord("felt", 4.7, 4.9),
            ProviderWord("happy", 5.0, 5.3),
        ),
    )
    first = calculate_speech_metrics(transcription, 6)
    second = calculate_speech_metrics(transcription, 6)

    assert first == second
    assert first.word_count == 9
    assert first.sentence_count == 2
    assert first.filler_rate_per_100_words == 11.1
    assert first.repeated_phrases == ["i"]
    assert first.acoustic.initial_response_delay_seconds == 0.5
    assert first.acoustic.long_pause_count == 2
    assert first.acoustic.silence_ratio > 0


def test_empty_timestamp_metrics_do_not_divide_by_zero() -> None:
    metrics = calculate_speech_metrics(
        ProviderTranscription(text="Hello", model="base.en"),
        1,
    )
    assert metrics.word_count == 1
    assert metrics.words_per_minute == 60
    assert metrics.acoustic.confidence == "low"
