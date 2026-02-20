from functools import lru_cache
import os

from faster_whisper import WhisperModel

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base.en")


@lru_cache(maxsize=1)
def _get_whisper_model():
    return WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")


def transcribe_audio(audio_path: str) -> str:
    model = _get_whisper_model()
    segments, _info = model.transcribe(audio_path, vad_filter=True, language="en", beam_size=1)
    text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()

    if not text:
        raise ValueError("El texto transcrito está vacío. Verifica el audio de entrada.")

    return text
