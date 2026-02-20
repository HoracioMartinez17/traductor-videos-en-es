from deep_translator import GoogleTranslator

from video_translator.utils.text import split_text


def translate_text(text: str) -> str:
    text_parts = split_text(text, max_length=500)
    translator = GoogleTranslator(source="en", target="es")
    translated_text_parts: list[str] = []

    for part in text_parts:
        translated_part = translator.translate(part)
        if translated_part:
            translated_text_parts.append(translated_part)

    translated_text = " ".join(translated_text_parts).strip()

    if not translated_text:
        raise ValueError("Error al traducir el texto. La traducción es nula o vacía.")

    return translated_text
