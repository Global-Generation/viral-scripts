import os
import logging
import httpx
import higgsfield_client
from database import SessionLocal
from models import ApiUsage

logger = logging.getLogger(__name__)

# Camera movement presets available in Cinema Studio
CAMERA_MOVEMENTS = [
    "", "dolly_forward", "dolly_backward", "pan_left", "pan_right",
    "tilt_up", "tilt_down", "orbit_left", "orbit_right",
    "zoom_in", "zoom_out", "fpv_drone", "crane_up", "crane_down",
    "tracking_left", "tracking_right", "static",
]

# Available models
VIDEO_MODELS = [
    "higgsfield-ai/dop/standard",
    "kling-video/v2.1/pro/image-to-video",
    "bytedance/seedance/v1/pro/image-to-video",
]

IMAGE_MODEL = "higgsfield-ai/soul/standard"
IMAGE_CHARACTER_MODEL = "higgsfield-ai/soul/character"


def _ensure_env():
    """Set HF_KEY env var from config if not already set."""
    if not os.environ.get("HF_KEY"):
        from config import HF_API_KEY, HF_API_SECRET
        if HF_API_KEY and HF_API_SECRET:
            os.environ["HF_KEY"] = f"{HF_API_KEY}:{HF_API_SECRET}"


def _log_usage(platform: str, model_id: str, request_type: str,
               request_id: str = "", status: str = ""):
    """Log an API call to ApiUsage table."""
    db = SessionLocal()
    try:
        usage = ApiUsage(
            platform=platform,
            model_id=model_id,
            request_type=request_type,
            request_id=request_id,
            status=status,
        )
        db.add(usage)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")
        db.rollback()
    finally:
        db.close()


def generate_avatar_image(prompt: str, aspect_ratio: str = "9:16") -> dict:
    """Generate a reference image for an avatar via text-to-image."""
    _ensure_env()
    try:
        controller = higgsfield_client.submit(
            IMAGE_MODEL,
            arguments={
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "quality": "2k",
            }
        )
        request_id = controller.request_id if hasattr(controller, "request_id") else ""
        _log_usage("higgsfield", IMAGE_MODEL, "image", request_id=str(request_id), status="queued")
        return {"request_id": str(request_id), "status": "queued"}
    except Exception as e:
        logger.error(f"Avatar image generation failed: {e}")
        _log_usage("higgsfield", IMAGE_MODEL, "image", status="failed")
        return {"request_id": "", "status": "failed", "error": str(e)}


def generate_variant_image(source_image_url: str, prompt: str,
                           strength: float = 0.3,
                           aspect_ratio: str = "9:16") -> dict:
    """Generate a variant image using character mode (preserves face identity from source)."""
    _ensure_env()
    try:
        controller = higgsfield_client.submit(
            IMAGE_CHARACTER_MODEL,
            arguments={
                "image_url": source_image_url,
                "prompt": prompt,
                "strength": strength,
                "aspect_ratio": aspect_ratio,
            }
        )
        request_id = controller.request_id if hasattr(controller, "request_id") else ""
        _log_usage("higgsfield", IMAGE_CHARACTER_MODEL, "image", request_id=str(request_id), status="queued")
        return {"request_id": str(request_id), "status": "queued"}
    except Exception as e:
        logger.error(f"Character image generation failed: {e}")
        _log_usage("higgsfield", IMAGE_CHARACTER_MODEL, "image", status="failed")
        return {"request_id": "", "status": "failed", "error": str(e)}


def generate_video(image_url: str, prompt: str, duration: int = 5,
                   aspect_ratio: str = "9:16", camera_movement: str = "",
                   sound: bool = False, slow_motion: bool = False,
                   speed_ramp: str = "auto", end_image: str = "",
                   model_id: str = "higgsfield-ai/dop/standard") -> dict:
    """Generate a video from an image via Cinema Studio."""
    _ensure_env()
    try:
        arguments = {
            "image_url": image_url,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": "1080p",
        }
        if camera_movement:
            arguments["camera_movement"] = camera_movement
        if sound:
            arguments["sound"] = True
        if slow_motion:
            arguments["slow_motion"] = True
        if speed_ramp and speed_ramp != "auto":
            arguments["speed_ramp"] = speed_ramp
        if end_image:
            arguments["end_image"] = end_image

        controller = higgsfield_client.submit(model_id, arguments=arguments)
        request_id = controller.request_id if hasattr(controller, "request_id") else ""
        _log_usage("higgsfield", model_id, "video", request_id=str(request_id), status="queued")
        return {"request_id": str(request_id), "status": "queued"}
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        _log_usage("higgsfield", model_id, "video", status="failed")
        return {"request_id": "", "status": "failed", "error": str(e)}


def check_status(request_id: str) -> dict:
    """Check the status of a Higgsfield request."""
    _ensure_env()
    try:
        status = higgsfield_client.status(request_id=request_id)
        if isinstance(status, higgsfield_client.Completed):
            result = higgsfield_client.result(request_id=request_id)
            # Extract URL from result
            url = ""
            if isinstance(result, dict):
                if "video" in result:
                    url = result["video"].get("url", "")
                elif "videos" in result and result["videos"]:
                    url = result["videos"][0].get("url", "")
                elif "images" in result and result["images"]:
                    url = result["images"][0].get("url", "")
                elif "url" in result:
                    url = result["url"]
            return {"status": "completed", "url": url, "result": result}
        elif isinstance(status, higgsfield_client.Failed):
            return {"status": "failed", "error": str(status)}
        elif isinstance(status, higgsfield_client.NSFW):
            return {"status": "nsfw", "error": "Content flagged as NSFW"}
        elif isinstance(status, higgsfield_client.Cancelled):
            return {"status": "cancelled"}
        elif isinstance(status, higgsfield_client.InProgress):
            return {"status": "in_progress"}
        elif isinstance(status, higgsfield_client.Queued):
            return {"status": "queued"}
        else:
            return {"status": "unknown", "raw": str(status)}
    except Exception as e:
        logger.error(f"Status check failed for {request_id}: {e}")
        return {"status": "error", "error": str(e)}


def cancel_request(request_id: str) -> bool:
    """Cancel a pending Higgsfield request."""
    _ensure_env()
    try:
        higgsfield_client.cancel(request_id=request_id)
        return True
    except Exception as e:
        logger.error(f"Cancel failed for {request_id}: {e}")
        return False


# === Soul ID (Custom References) ===

PLATFORM_URL = "https://platform.higgsfield.ai"


def _get_auth_header() -> dict:
    """Get authorization header for direct API calls."""
    _ensure_env()
    hf_key = os.environ.get("HF_KEY", "")
    return {"Authorization": f"Key {hf_key}"}


def create_soul_id(name: str, image_urls: list[str]) -> dict:
    """Train a Soul ID from reference images. Returns soul_id or error."""
    try:
        headers = _get_auth_header()
        headers["Content-Type"] = "application/json"
        payload = {
            "name": name,
            "input_images": [
                {"type": "image_url", "image_url": url} for url in image_urls
            ]
        }
        resp = httpx.post(
            f"{PLATFORM_URL}/v1/custom-references",
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        soul_id = data.get("id", "")
        logger.info(f"Soul ID training started: {soul_id}")
        _log_usage("higgsfield", "soul-id", "train", request_id=str(soul_id), status="training")
        return {"soul_id": str(soul_id), "status": "training"}
    except Exception as e:
        logger.error(f"Soul ID creation failed: {e}")
        return {"soul_id": "", "status": "failed", "error": str(e)}


def check_soul_id_status(soul_id: str) -> dict:
    """Check Soul ID training status. Returns status: training/ready/failed."""
    try:
        headers = _get_auth_header()
        resp = httpx.get(
            f"{PLATFORM_URL}/v1/custom-references/{soul_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "").upper()
        if status == "COMPLETED":
            return {"status": "ready"}
        elif status in ("FAILED", "ERROR"):
            return {"status": "failed", "error": data.get("error", "")}
        else:  # NOT_READY, QUEUED, IN_PROGRESS
            return {"status": "training"}
    except Exception as e:
        logger.error(f"Soul ID status check failed: {e}")
        return {"status": "error", "error": str(e)}


def generate_with_soul_id(soul_id: str, prompt: str,
                          aspect_ratio: str = "9:16") -> dict:
    """Generate image using trained Soul ID for perfect face preservation."""
    _ensure_env()
    try:
        controller = higgsfield_client.submit(
            IMAGE_MODEL,
            arguments={
                "prompt": prompt,
                "custom_reference_id": soul_id,
                "custom_reference_strength": 1.0,
                "aspect_ratio": aspect_ratio,
                "quality": "2k",
            }
        )
        request_id = controller.request_id if hasattr(controller, "request_id") else ""
        _log_usage("higgsfield", IMAGE_MODEL, "image-soul", request_id=str(request_id), status="queued")
        return {"request_id": str(request_id), "status": "queued"}
    except Exception as e:
        logger.error(f"Soul ID generation failed: {e}")
        return {"request_id": "", "status": "failed", "error": str(e)}
