from video_translator.utils.shared.video_pipeline import process_video_pipeline

async def process_and_translate(input_path: str, output_path: str, extract_audio, transcribe_audio, translate_text, generate_audio, replace_audio) -> None:
    def on_step(step: str, payload: str | None) -> None:
        if step == "extract_audio:start":
            print("  🎵 Extrayendo audio...")
        elif step == "transcribe:start":
            print("  🎤 Transcribiendo...")
        elif step == "transcribe:done" and payload is not None:
            print(f"  📝 Transcrito: {payload}...")
        elif step == "translate:start":
            print("  🌐 Traduciendo...")
        elif step == "translate:done" and payload is not None:
            print(f"  ✅ Traducido: {payload}...")
        elif step == "tts:start":
            print("  🔊 Generando audio traducido...")
        elif step == "replace_audio:start":
            print("  🎬 Reemplazando audio en video...")
        elif step == "pipeline:done":
            print("  ✅ Video procesado correctamente")

    await process_video_pipeline(
        input_path,
        output_path,
        extract_audio,
        transcribe_audio,
        translate_text,
        generate_audio,
        replace_audio,
        on_step=on_step,
    )
