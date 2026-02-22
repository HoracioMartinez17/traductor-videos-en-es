import argparse
import asyncio
import os

import httpx

from video_translator.services.media_service import extract_audio, replace_audio
from video_translator.services.transcription_service import transcribe_audio
from video_translator.services.translation_service import translate_text
from video_translator.services.tts_service import generate_audio
from video_translator.utils.worker.validate_video_duration import validate_video_duration
from video_translator.utils.worker import (
    claim_job,
    cleanup_temp_files,
    download_file_from_api,
    download_youtube_video,
    get_youtube_duration,
    get_next_job,
    is_supported_youtube_url,
    mark_failed,
    process_and_translate,
    upload_file_to_api,
)


class Worker:
    def __init__(self, api_url: str, api_key: str, worker_id: str | None = None):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.worker_id = worker_id or "default-worker"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0),
            headers={"X-API-Key": api_key},
        )

    async def get_next_job(self):
        return await get_next_job(self.client, self.api_url, self.worker_id)

    async def claim_job(self, job_id: str) -> bool:
        return await claim_job(self.client, self.api_url, job_id, self.worker_id)

    async def download_input(self, job_id: str, local_path: str):
        return await download_file_from_api(self.client, self.api_url, job_id, local_path)

    async def process_video(self, input_path: str, output_path: str):
        await process_and_translate(
            input_path,
            output_path,
            extract_audio,
            transcribe_audio,
            translate_text,
            generate_audio,
            replace_audio,
        )

    async def upload_result(self, job_id: str, output_path: str):
        return await upload_file_to_api(self.client, self.api_url, job_id, output_path)

    async def mark_failed(self, job_id: str, error_message: str):
        await mark_failed(self.client, self.api_url, job_id, self.worker_id, error_message)

    async def process_job(self, job):
        job_id = job["id"]
        input_path = job.get("input_path")

        print(f"\n🚀 Procesando job {job_id}")

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            local_input = os.path.join(tmpdir, "input.mp4")
            local_output = os.path.join(tmpdir, "output.mp4")

            try:
                if input_path and is_supported_youtube_url(input_path):
                    duration = get_youtube_duration(input_path)
                    if duration > 300:
                        duration_seconds = int(duration)
                        minutes = duration_seconds // 60
                        seconds = duration_seconds % 60
                        raise ValueError(
                            "Hermano, te pasaste 😅 ¿Qué piensas, que tengo un ordenador de la NASA o qué? "
                            "El límite es de 5 minutos por video "
                            f"y este dura {minutes}:{seconds:02d}."
                        )
                    await download_youtube_video(input_path, local_input)
                    validate_video_duration(local_input)
                else:
                    await self.download_input(job_id, local_input)

                await self.process_video(local_input, local_output)

                if await self.upload_result(job_id, local_output):
                    print(f"✅ Job {job_id} completado exitosamente")
                else:
                    await self.mark_failed(job_id, "Error al subir resultado")

            except Exception as error:
                print(f"❌ Error procesando job {job_id}: {error}")
                await self.mark_failed(job_id, str(error))
            finally:
                cleanup_temp_files(local_input, local_output)

    async def run(self, poll_interval: int = 5):
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
