import httpx

async def download_file_from_api(client: httpx.AsyncClient, api_url: str, job_id: str, local_path: str) -> str:
    print("  ⬇️  Descargando video de entrada...")
    try:
        async with client.stream("GET", f"{api_url}/jobs/{job_id}/download-input") as response:
            response.raise_for_status()
            with open(local_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        print(f"  ✅ Descargado a {local_path}")
        return local_path
    except Exception as error:
        print(f"❌ Error al descargar input: {error}")
        raise
