import threading
from io import BytesIO
from types import SimpleNamespace

import pytest

from app.providers.local_whisper_provider import LocalWhisperTranscriptionProvider


class FakeWhisperModel:
    def __init__(self) -> None:
        self.audio: bytes | None = None
        self.kwargs: dict[str, object] | None = None
        self.thread_id: int | None = None

    def transcribe(self, audio: BytesIO, **kwargs: object):
        self.kwargs = kwargs
        self.thread_id = threading.get_ident()

        def segments():
            self.audio = audio.read()
            yield SimpleNamespace(text=" Um,")
            yield SimpleNamespace(text=" I I went there.")

        return segments(), SimpleNamespace(duration=4.25)


@pytest.mark.asyncio
async def test_local_whisper_adapts_audio_without_rewriting_spoken_text() -> None:
    model = FakeWhisperModel()
    loader_calls: list[str] = []

    def load_model() -> FakeWhisperModel:
        loader_calls.append("loaded")
        return model

    provider = LocalWhisperTranscriptionProvider(
        model_loader=load_model, model_name="small.en"
    )
    request_thread_id = threading.get_ident()

    result = await provider.transcribe(
        audio=b"recorded audio",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="preserve every audible filler",
    )

    assert model.audio == b"recorded audio"
    assert loader_calls == ["loaded"]
    assert model.kwargs == {"language": "en", "task": "transcribe", "vad_filter": False}
    assert model.thread_id != request_thread_id
    assert result.text == " Um, I I went there."
    assert result.model == "local-whisper/small.en"
    assert result.audio_seconds == 4.25
    assert result.usage is None
    assert result.token_logprobs == ()
