import httpx

async def mark_failed(client: httpx.AsyncClient, api_url: str, job_id: str, worker_id: str, error_message: str):
    """Marca un job como fallido."""
    try:
        await client.post(
            f"{api_url}/jobs/{job_id}/complete",
            params={
                "worker_id": worker_id,
                "success": False,
                "error_message": error_message,
            },
        )
    except Exception as error:
        print(f"❌ Error al marcar job como fallido: {error}")
