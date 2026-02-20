import httpx

async def upload_file_to_api(client: httpx.AsyncClient, api_url: str, job_id: str, output_path: str) -> bool:
    print("  ⬆️  Subiendo resultado...")
    try:
        with open(output_path, "rb") as f:
            files = {"file": ("output.mp4", f, "video/mp4")}
            response = await client.post(
                f"{api_url}/jobs/{job_id}/upload-result",
                files=files,
            )
            response.raise_for_status()
        print("  ✅ Resultado subido correctamente")
        return True
    except Exception as error:
        print(f"❌ Error al subir resultado: {error}")
        return False
