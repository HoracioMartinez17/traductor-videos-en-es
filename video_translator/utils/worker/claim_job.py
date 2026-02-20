import httpx

async def claim_job(client: httpx.AsyncClient, api_url: str, job_id: str, worker_id: str) -> bool:
    """Reclama un job para procesarlo."""
    try:
        response = await client.post(
            f"{api_url}/jobs/{job_id}/claim", params={"worker_id": worker_id}
        )
        response.raise_for_status()
        return True
    except Exception as error:
        print(f"❌ Error al reclamar job {job_id}: {error}")
        return False
