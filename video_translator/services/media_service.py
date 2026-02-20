import json
import subprocess


def get_video_duration(video_path: str) -> float:
    """Obtiene la duración del video en segundos usando ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def extract_audio(video_path: str, audio_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "copy", audio_path],
        check=True,
    )


def replace_audio(video_path: str, audio_path: str, output_video: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            output_video,
        ],
        check=True,
    )
