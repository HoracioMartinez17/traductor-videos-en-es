def humanize_url_download_error(error: Exception) -> str:
    raw = str(error)
    normalized = raw.lower()
    if "sign in to confirm you're not a bot" in normalized or "cookies" in normalized:
        return "YouTube bloqueó la descarga automática de este video. Prueba con otro enlace público o sube un archivo local."
    if "private video" in normalized or "this video is private" in normalized:
        return "El video es privado y no se puede descargar. Usa un enlace público."
    if "video unavailable" in normalized or "unavailable" in normalized:
        return "El video no está disponible. Verifica la URL o prueba otro enlace."
    return "No se pudo descargar el video desde la URL. Verifica el enlace o sube un archivo local."
