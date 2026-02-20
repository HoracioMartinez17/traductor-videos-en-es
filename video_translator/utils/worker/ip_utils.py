from fastapi import Request, HTTPException
from video_translator.models.job import register_ip_request

MAX_REQUESTS_PER_IP = 13
IP_LIMIT_BYPASS = {
    ip.strip()
    for ip in ("127.0.0.1,::1").split(",")
    if ip.strip()
}

def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"

def enforce_ip_limit(request: Request) -> None:
    client_ip = get_client_ip(request)
    if client_ip in IP_LIMIT_BYPASS:
        return
    allowed, total_requests = register_ip_request(client_ip, MAX_REQUESTS_PER_IP)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                "Límite de uso alcanzado para esta IP (máximo 13 envíos). "
                f"Intentos registrados: {total_requests}."
            ),
        )
