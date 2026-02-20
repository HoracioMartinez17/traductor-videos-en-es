import httpx

async def get_next_job(client: httpx.AsyncClient, api_url: str, worker_id: str) -> dict | None:
    """Obtiene el siguiente job pendiente."""
    try:
        response = await client.get(f"{api_url}/jobs/next", params={"worker_id": worker_id})
        response.raise_for_status()
        data = response.json()
        return data.get("job")
    except Exception as error:
        print(f"❌ Error al obtener job: {error}")
        return None
