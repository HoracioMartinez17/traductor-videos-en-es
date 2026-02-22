import inspect
import os
import tempfile
from collections.abc import Callable
from typing import Any


StepHook = Callable[[str, str | None], None]


async def _maybe_await(func: Callable[..., Any], *args: Any) -> Any:
    result = func(*args)
    if inspect.isawaitable(result):
        return await result
    return result


async def process_video_pipeline(
    input_path: str,
    output_path: str,
    extract_audio: Callable[..., Any],
    transcribe_audio: Callable[..., Any],
    translate_text: Callable[..., Any],
    generate_audio: Callable[..., Any],
    replace_audio: Callable[..., Any],
    on_step: StepHook | None = None,
) -> None:
    with tempfile.NamedTemporaryFile(suffix=".aac", delete=False) as temp_audio, tempfile.NamedTemporaryFile(
        suffix=".mp3", delete=False
    ) as temp_output_audio:
        try:
            if on_step:
                on_step("extract_audio:start", None)
            await _maybe_await(extract_audio, input_path, temp_audio.name)

            if on_step:
                on_step("transcribe:start", None)
            transcribed_text = await _maybe_await(transcribe_audio, temp_audio.name)
            if on_step:
                on_step("transcribe:done", str(transcribed_text)[:100])

            if on_step:
                on_step("translate:start", None)
            translated_text = await _maybe_await(translate_text, transcribed_text)
            if on_step:
                on_step("translate:done", str(translated_text)[:100])

            if on_step:
                on_step("tts:start", None)
            await _maybe_await(generate_audio, translated_text, temp_output_audio.name)

            if on_step:
                on_step("replace_audio:start", None)
            await _maybe_await(replace_audio, input_path, temp_output_audio.name, output_path)
            if on_step:
                on_step("pipeline:done", None)
        finally:
            if os.path.exists(temp_audio.name):
                os.remove(temp_audio.name)
            if os.path.exists(temp_output_audio.name):
                os.remove(temp_output_audio.name)
