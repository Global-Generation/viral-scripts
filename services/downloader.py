import os
import logging
import threading
import yt_dlp
from config import DOWNLOADS_DIR

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = 60  # seconds

os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def download_audio(tiktok_url: str, video_id: int) -> str:
    output_path = os.path.join(DOWNLOADS_DIR, f"video_{video_id}.%(ext)s")
    final_path = os.path.join(DOWNLOADS_DIR, f"video_{video_id}.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "64",
        }],
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    }

    error_box = [None]

    def _run():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([tiktok_url])
        except Exception as e:
            error_box[0] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=DOWNLOAD_TIMEOUT)

    if t.is_alive():
        raise RuntimeError(f"Download timed out after {DOWNLOAD_TIMEOUT}s")
    if error_box[0]:
        raise error_box[0]

    if not os.path.exists(final_path):
        raise FileNotFoundError(f"Downloaded file not found at {final_path}")

    return final_path


def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning(f"Failed to delete {path}: {e}")
