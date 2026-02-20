from functools import lru_cache

import whisper


@lru_cache(maxsize=1)
def _get_whisper_model():
    return whisper.load_model("base")


def transcribe_audio(audio_path: str) -> str:
    model = _get_whisper_model()
    result = model.transcribe(audio_path)

    if result is None or "text" not in result:
        raise ValueError("Error al transcribir el audio. El resultado es nulo o no contiene texto.")

    text_value = result.get("text", "")
    text = text_value.strip() if isinstance(text_value, str) else ""

    if not text:
        raise ValueError("El texto transcrito está vacío. Verifica el audio de entrada.")

    return text
