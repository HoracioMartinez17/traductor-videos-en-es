import os

import edge_tts


async def generate_audio(text: str, output_audio: str, voice: str = "es-PE-AlexNeural") -> None:
    if not text:
        raise ValueError("El texto para generar audio está vacío.")

    tts = edge_tts.Communicate(text, voice)
    await tts.save(output_audio)

    if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
        raise ValueError("El archivo de audio generado está vacío.")
