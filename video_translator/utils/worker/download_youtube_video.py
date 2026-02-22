from video_translator.utils.shared.yt_dlp_utils import download_with_fallback

async def download_youtube_video(url: str, local_path: str) -> None:
    print("  ⬇️  Descargando video de YouTube localmente...")
    ydl_opts = {
        "format": "mp4/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": local_path,
        "merge_output_format": "mp4",
    }

    browser_used = download_with_fallback(url, ydl_opts)
    if browser_used:
        print(f"  ✅ Descargado a {local_path} (usando cookies de {browser_used})")
        return

    print(f"  ✅ Descargado a {local_path}")
