import os
import logging
import subprocess
import urllib.request

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "./downloads")

_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _download(url: str, path: str) -> str:
    """Download a URL with proper headers to avoid CDN 403."""
    os.makedirs(os.path.dirname(path) or DOWNLOADS_DIR, exist_ok=True)
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp, open(path, "wb") as f:
        while chunk := resp.read(1024 * 64):
            f.write(chunk)
    return path


def extract_last_frame(video_url: str, output_path: str = "") -> str:
    """Download video and extract the last frame as a PNG image.

    Returns the path to the extracted frame image.
    """
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    if not output_path:
        output_path = os.path.join(DOWNLOADS_DIR, f"endframe_{os.urandom(4).hex()}.png")

    tmp_video = os.path.join(DOWNLOADS_DIR, f"tmp_endframe_{os.urandom(4).hex()}.mp4")
    try:
        logger.info(f"Downloading video for end frame extraction: {video_url[:80]}")
        _download(video_url, tmp_video)

        # Get total number of frames
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
             "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", tmp_video],
            capture_output=True, text=True, timeout=30,
        )
        total_frames = int(probe.stdout.strip()) if probe.stdout.strip() else 0

        if total_frames > 0:
            # Extract last frame using frame number
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_video, "-vf", f"select=eq(n\\,{total_frames - 1})",
                 "-frames:v", "1", output_path],
                check=True, capture_output=True, timeout=30,
            )
        else:
            # Fallback: seek to end and grab a frame
            subprocess.run(
                ["ffmpeg", "-y", "-sseof", "-0.1", "-i", tmp_video,
                 "-frames:v", "1", "-update", "1", output_path],
                check=True, capture_output=True, timeout=30,
            )

        logger.info(f"Extracted end frame to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"End frame extraction failed: {e}")
        raise
    finally:
        if os.path.exists(tmp_video):
            os.remove(tmp_video)


def concat_videos(video_paths: list[str], output_path: str) -> str:
    """Concatenate multiple video files into one using ffmpeg.

    All videos are re-encoded to ensure compatible streams.
    Returns the output path.
    """
    os.makedirs(os.path.dirname(output_path) or DOWNLOADS_DIR, exist_ok=True)

    if len(video_paths) == 1:
        # Just copy the single video
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_paths[0], "-c", "copy",
             "-movflags", "+faststart", output_path],
            check=True, capture_output=True, timeout=120,
        )
        return output_path

    # Create concat filter with re-encoding for compatibility
    filter_parts = []
    inputs = []
    for i, path in enumerate(video_paths):
        inputs.extend(["-i", path])
        filter_parts.append(f"[{i}:v:0][{i}:a:0]")

    filter_str = "".join(filter_parts) + f"concat=n={len(video_paths)}:v=1:a=1[outv][outa]"

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_str,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info(f"Concatenating {len(video_paths)} videos into {output_path}")
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    logger.info(f"Concat complete: {output_path}")
    return output_path


def download_video(url: str, output_path: str) -> str:
    """Download a video from URL to local path."""
    return _download(url, output_path)
