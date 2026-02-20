#!/usr/bin/env python3
"""
Worker para procesamiento distribuido de traducción de videos.

Uso:
    python worker.py --api-url https://api.example.com --api-key <token>

Proceso:
1. Polling de jobs pendientes en la API
2. Descarga del video de entrada
3. Procesamiento local (transcripción, traducción, TTS)
4. Upload del resultado procesado
"""

import argparse
import asyncio
import os
import socket
import tempfile
import time
from pathlib import Path

import httpx

# Importar servicios de procesamiento
import sys

sys.path.insert(0, str(Path(__file__).parent))

from video_translator.services.media_service import extract_audio, replace_audio
from video_translator.services.transcription_service import transcribe_audio
from video_translator.services.translation_service import translate_text
from video_translator.services.tts_service import generate_audio


class Worker:
    def __init__(self, api_url: str, api_key: str, worker_id: str | None = None):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0),
            headers={"X-API-Key": api_key},
        )

    async def get_next_job(self):
        """Obtiene el siguiente job pendiente."""
        try:
            response = await self.client.get(f"{self.api_url}/jobs/next", params={"worker_id": self.worker_id})
            response.raise_for_status()
            data = response.json()
            return data.get("job")
        except Exception as error:
            print(f"❌ Error al obtener job: {error}")
            return None

    async def claim_job(self, job_id: str) -> bool:
        """Reclama un job para procesarlo."""
        try:
            response = await self.client.post(
                f"{self.api_url}/jobs/{job_id}/claim", params={"worker_id": self.worker_id}
            )
            response.raise_for_status()
            return True
        except Exception as error:
            print(f"❌ Error al reclamar job {job_id}: {error}")
            return False

    async def download_input(self, job_id: str, local_path: str):
        """Descarga el video de entrada desde la API."""
        try:
            print("  ⬇️  Descargando video de entrada...")
            async with self.client.stream("GET", f"{self.api_url}/jobs/{job_id}/download-input") as response:
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
            print(f"  ✅ Descargado a {local_path}")
            return local_path
        except Exception as error:
            print(f"❌ Error al descargar input: {error}")
            raise

    async def process_video(self, input_path: str, output_path: str):
        """Procesa el video localmente."""
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

    async def upload_result(self, job_id: str, output_path: str):
        """Sube el resultado al servidor."""
        try:
            print("  ⬆️  Subiendo resultado...")
            with open(output_path, "rb") as f:
                files = {"file": ("output.mp4", f, "video/mp4")}
                response = await self.client.post(
                    f"{self.api_url}/jobs/{job_id}/upload-result",
                    files=files,
                )
                response.raise_for_status()
            print("  ✅ Resultado subido correctamente")
            return True
        except Exception as error:
            print(f"❌ Error al subir resultado: {error}")
            return False

    async def mark_failed(self, job_id: str, error_message: str):
        """Marca un job como fallido."""
        try:
            await self.client.post(
                f"{self.api_url}/jobs/{job_id}/complete",
                params={
                    "worker_id": self.worker_id,
                    "success": False,
                    "error_message": error_message,
                },
            )
        except Exception as error:
            print(f"❌ Error al marcar job como fallido: {error}")

    async def process_job(self, job):
        """Procesa un job completo."""
        job_id = job["id"]

        print(f"\n🚀 Procesando job {job_id}")

        # Crear directorio temporal para este job
        with tempfile.TemporaryDirectory() as tmpdir:
            local_input = os.path.join(tmpdir, "input.mp4")
            local_output = os.path.join(tmpdir, "output.mp4")

            try:
                # Descargar input
                await self.download_input(job_id, local_input)

                # Procesar
                await self.process_video(local_input, local_output)

                # Subir resultado
                if await self.upload_result(job_id, local_output):
                    print(f"✅ Job {job_id} completado exitosamente")
                else:
                    await self.mark_failed(job_id, "Error al subir resultado")

            except Exception as error:
                print(f"❌ Error procesando job {job_id}: {error}")
                await self.mark_failed(job_id, str(error))

    async def run(self, poll_interval: int = 5):
        """Loop principal del worker."""
        print(f"🤖 Worker iniciado: {self.worker_id}")
        print(f"🌐 API: {self.api_url}")
        print(f"⏱️  Intervalo de polling: {poll_interval}s\n")

        try:
            while True:
                job = await self.get_next_job()

                if job:
                    await self.process_job(job)
                else:
                    print("⏸️  No hay jobs pendientes, esperando...")
                    await asyncio.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n\n👋 Worker detenido por el usuario")
        finally:
            await self.client.aclose()


def main():
    parser = argparse.ArgumentParser(description="Worker de procesamiento de videos")
    parser.add_argument("--api-url", required=True, help="URL base de la API")
    parser.add_argument("--api-key", required=True, help="Token de autenticación")
    parser.add_argument("--poll-interval", type=int, default=5, help="Intervalo de polling en segundos")
    parser.add_argument("--worker-id", help="Identificador del worker")

    args = parser.parse_args()

    worker = Worker(api_url=args.api_url, api_key=args.api_key, worker_id=args.worker_id)

    asyncio.run(worker.run(poll_interval=args.poll_interval))


if __name__ == "__main__":
    main()
