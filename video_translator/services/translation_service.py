from functools import lru_cache
from typing import Any, cast

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from video_translator.utils.text_utils import split_text


@lru_cache(maxsize=1)
def _get_translation_resources() -> tuple[Any, Any]:
    tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-es")
    model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-en-es")
    return tokenizer, model


def translate_text(text: str) -> str:
    text_parts = split_text(text, max_length=500)
    tokenizer, model = _get_translation_resources()

    translated_text_parts: list[str] = []
    generation_model = cast(Any, model)
    generation_tokenizer = cast(Any, tokenizer)

    for part in text_parts:
        encoded_inputs = generation_tokenizer(part, return_tensors="pt", truncation=True, max_length=512)
        input_ids = encoded_inputs["input_ids"]
        attention_mask = encoded_inputs.get("attention_mask")

        if attention_mask is not None:
            generated_tokens = generation_model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=512,
            )
        else:
            generated_tokens = generation_model.generate(input_ids=input_ids, max_length=512)

        decoded_part = generation_tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
        translated_part = decoded_part if isinstance(decoded_part, str) else " ".join(decoded_part)
        translated_text_parts.append(translated_part)

    translated_text = " ".join(translated_text_parts).strip()

    if not translated_text:
        raise ValueError("Error al traducir el texto. La traducción es nula o vacía.")

    return translated_text
