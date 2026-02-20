import os
import tempfile

async def process_and_translate(input_path: str, output_path: str, extract_audio, transcribe_audio, translate_text, generate_audio, replace_audio) -> None:
    with tempfile.NamedTemporaryFile(suffix=".aac", delete=False) as temp_audio, tempfile.NamedTemporaryFile(
        suffix=".mp3", delete=False
    ) as temp_output_audio:
        try:
            print("  🎵 Extrayendo audio...")
            extract_audio(input_path, temp_audio.name)

            print("  🎤 Transcribiendo...")
            transcribed_text = transcribe_audio(temp_audio.name)
            print(f"  📝 Transcrito: {transcribed_text[:100]}...")

            print("  🌐 Traduciendo...")
            translated_text = translate_text(transcribed_text)
            print(f"  ✅ Traducido: {translated_text[:100]}...")

            print("  🔊 Generando audio traducido...")
            await generate_audio(translated_text, temp_output_audio.name)

            print("  🎬 Reemplazando audio en video...")
            replace_audio(input_path, temp_output_audio.name, output_path)

            print("  ✅ Video procesado correctamente")
        finally:
            if os.path.exists(temp_audio.name):
                os.remove(temp_audio.name)
            if os.path.exists(temp_output_audio.name):
                os.remove(temp_output_audio.name)
