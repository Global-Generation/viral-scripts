import logging
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse, Response
from typing import Literal
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Video, Script, Avatar, VideoGeneration
from services.pipeline import extract_script_for_video
from services.higgsfield import generate_video, check_status as hf_check_status
from services.rewriter import rewrite_provocative
from services.classifier import classify_script
from services.scorer import score_viral_potential
from services.prompter import generate_video_prompt
from services.subtitler import add_subtitles

router = APIRouter(prefix="/api/scripts", tags=["scripts"])
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=8)


@router.post("/extract/{video_id}")
def extract_script(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).get(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status == "extracting":
        return {"ok": True, "message": "Already extracting"}
    if video.status == "extracted" and video.script:
        return {"ok": True, "script_id": video.script.id, "already_done": True}

    _executor.submit(extract_script_for_video, video_id)
    return {"ok": True, "message": "Extraction started"}


@router.get("/{script_id}")
def get_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {
        "id": script.id,
        "video_id": script.video_id,
        "original_text": script.original_text,
        "modified_text": script.modified_text,
        "character_type": script.character_type,
        "viral_score": script.viral_score,
        "assigned_to": script.assigned_to,
        "production_status": script.production_status or "",
        "published_tiktok": script.published_tiktok.isoformat() if script.published_tiktok else None,
        "published_youtube": script.published_youtube.isoformat() if script.published_youtube else None,
        "published_instagram": script.published_instagram.isoformat() if script.published_instagram else None,
        "video_prompt": script.video_prompt or "",
        "video1_prompt": script.video1_prompt or "",
        "video2_prompt": script.video2_prompt or "",
        "video3_prompt": script.video3_prompt or "",
        "status": script.status,
    }


VALID_ASSIGNEES = {"boris", "thomas", "daniel", "zoe", "natalie", "luna", ""}


class AssignRequest(BaseModel):
    assigned_to: str


class ProductionRequest(BaseModel):
    production_status: str


class PublishRequest(BaseModel):
    platform: str


class PublishDateRequest(BaseModel):
    platform: str
    date: str  # ISO date string or empty to clear


class BatchAssignRequest(BaseModel):
    script_ids: list[int]
    assigned_to: str


class ScriptUpdate(BaseModel):
    original_text: str = None
    modified_text: str = None
    video_prompt: str = None
    video1_prompt: str = None
    video2_prompt: str = None
    video3_prompt: str = None


@router.put("/{script_id}")
def update_script(script_id: int, data: ScriptUpdate, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if data.original_text is not None:
        script.original_text = data.original_text
    if data.modified_text is not None:
        script.modified_text = data.modified_text
    if data.video_prompt is not None:
        script.video_prompt = data.video_prompt
    if data.video1_prompt is not None:
        script.video1_prompt = data.video1_prompt
    if data.video2_prompt is not None:
        script.video2_prompt = data.video2_prompt
    if data.video3_prompt is not None:
        script.video3_prompt = data.video3_prompt
    db.commit()
    return {"ok": True}


@router.post("/{script_id}/rewrite")
def rewrite_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if not script.original_text:
        raise HTTPException(status_code=400, detail="No script text to rewrite")

    rewritten = rewrite_provocative(script.original_text)
    script.modified_text = rewritten
    script.status = "modified"
    db.commit()
    return {"ok": True, "modified_text": rewritten}


@router.post("/{script_id}/classify")
def classify_one(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if not script.original_text:
        raise HTTPException(status_code=400, detail="No text to classify")
    char_type = classify_script(script.original_text)
    script.character_type = char_type
    db.commit()
    return {"ok": True, "character_type": char_type}


@router.post("/{script_id}/score")
def score_one(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if not script.original_text:
        raise HTTPException(status_code=400, detail="No text to score")
    vs = score_viral_potential(script.original_text)
    script.viral_score = vs
    db.commit()
    return {"ok": True, "viral_score": vs}


@router.post("/batch-extract")
def batch_extract(db: Session = Depends(get_db)):
    """Extract scripts from ALL videos that haven't been extracted yet."""
    videos = db.query(Video).filter(Video.status == "found").all()
    count = 0
    for video in videos:
        _executor.submit(extract_script_for_video, video.id)
        count += 1
    return {"ok": True, "queued": count}


@router.post("/batch-rewrite")
def batch_rewrite(db: Session = Depends(get_db)):
    """Rewrite ALL scripts that don't have a modified version yet."""
    scripts = db.query(Script).filter(
        Script.original_text != "",
        Script.original_text.isnot(None),
        (Script.modified_text == "") | (Script.modified_text.is_(None)),
    ).all()
    count = 0
    errors = 0
    for script in scripts:
        try:
            rewritten = rewrite_provocative(script.original_text)
            script.modified_text = rewritten
            script.status = "modified"
            db.commit()
            count += 1
            logger.info(f"Rewritten script #{script.id}")
        except Exception as e:
            errors += 1
            logger.error(f"Rewrite failed for script #{script.id}: {e}")
    return {"ok": True, "rewritten": count, "errors": errors}


@router.post("/{script_id}/assign")
def assign_script(script_id: int, data: AssignRequest, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if data.assigned_to not in VALID_ASSIGNEES:
        raise HTTPException(status_code=400, detail=f"Invalid assignee. Valid: {VALID_ASSIGNEES}")
    script.assigned_to = data.assigned_to
    db.commit()
    return {"ok": True, "assigned_to": data.assigned_to}


VALID_PRODUCTION_STATUSES = {"", "ready", "filmed", "published"}
VALID_PLATFORMS = {"tiktok", "youtube", "instagram"}


@router.post("/{script_id}/production")
def update_production(script_id: int, data: ProductionRequest, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if data.production_status not in VALID_PRODUCTION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {VALID_PRODUCTION_STATUSES}")
    script.production_status = data.production_status
    db.commit()
    return {"ok": True, "production_status": data.production_status}


@router.post("/{script_id}/publish")
def toggle_publish(script_id: int, data: PublishRequest, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if data.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform. Valid: {VALID_PLATFORMS}")
    col = f"published_{data.platform}"
    current = getattr(script, col)
    if current:
        setattr(script, col, None)
        db.commit()
        return {"ok": True, "published": False, "date": None}
    else:
        now = datetime.now(timezone.utc)
        setattr(script, col, now)
        db.commit()
        return {"ok": True, "published": True, "date": now.isoformat()}


@router.post("/{script_id}/publish-date")
def set_publish_date(script_id: int, data: PublishDateRequest, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if data.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform. Valid: {VALID_PLATFORMS}")
    col = f"published_{data.platform}"
    if data.date:
        dt = datetime.fromisoformat(data.date.replace('Z', '+00:00'))
        setattr(script, col, dt)
        db.commit()
        return {"ok": True, "date": dt.isoformat()}
    else:
        setattr(script, col, None)
        db.commit()
        return {"ok": True, "date": None}


@router.post("/batch-assign")
def batch_assign(data: BatchAssignRequest, db: Session = Depends(get_db)):
    if data.assigned_to not in VALID_ASSIGNEES:
        raise HTTPException(status_code=400, detail=f"Invalid assignee. Valid: {VALID_ASSIGNEES}")
    count = 0
    for sid in data.script_ids:
        script = db.query(Script).get(sid)
        if script:
            script.assigned_to = data.assigned_to
            count += 1
    db.commit()
    return {"ok": True, "assigned": count}


@router.post("/{script_id}/generate-prompt")
def generate_prompt(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    text = script.modified_text or script.original_text
    if not text:
        raise HTTPException(status_code=400, detail="No script text to generate prompt from")

    result = generate_video_prompt(text)
    script.video1_prompt = result["video1"]
    script.video2_prompt = result["video2"]
    script.video3_prompt = ""
    script.video_prompt = result["video1"] + "\n\n" + result["video2"]
    db.commit()
    return {"ok": True, "video1_prompt": result["video1"], "video2_prompt": result["video2"], "video3_prompt": ""}


@router.post("/batch-generate-prompts")
def batch_generate_prompts(db: Session = Depends(get_db)):
    """Generate video prompts for all assigned scripts that don't have one yet."""
    scripts = db.query(Script).filter(
        Script.assigned_to != "",
        Script.assigned_to.isnot(None),
        (Script.video1_prompt == "") | (Script.video1_prompt.is_(None)),
    ).all()
    count = 0
    errors = 0
    for script in scripts:
        text = script.modified_text or script.original_text
        if not text:
            continue
        try:
            result = generate_video_prompt(text)
            script.video1_prompt = result["video1"]
            script.video2_prompt = result["video2"]
            script.video3_prompt = ""
            script.video_prompt = result["video1"] + "\n\n" + result["video2"]
            db.commit()
            count += 1
            logger.info(f"Generated prompt for script #{script.id}")
        except Exception as e:
            errors += 1
            logger.error(f"Prompt generation failed for script #{script.id}: {e}")
    return {"ok": True, "generated": count, "errors": errors, "total_queued": len(scripts)}


class GenerateVideoRequest(BaseModel):
    video_number: int = 1
    avatar_id: int = None
    model_id: str = "higgsfield-ai/dop/standard"
    duration: Literal[5, 10] = 5
    aspect_ratio: str = "9:16"
    camera_movement: str = ""
    sound: bool = False
    slow_motion: bool = False
    speed_ramp: str = "auto"


class GenerateStepRequest(BaseModel):
    video_number: int = 1
    avatar_id: int = None
    model_id: str = "higgsfield-ai/dop/standard"
    duration: Literal[5, 10] = 5
    aspect_ratio: str = "9:16"
    camera_movement: str = ""
    sound: bool = False
    slow_motion: bool = False
    speed_ramp: str = "auto"
    end_frame_image: str = ""  # end frame from previous step


class SelectVariantRequest(BaseModel):
    video_number: int
    generation_id: int


@router.post("/{script_id}/generate-video")
def generate_video_endpoint(script_id: int, data: GenerateVideoRequest, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Get prompt text
    prompt_text = ""
    if data.video_number == 1:
        prompt_text = script.video1_prompt or ""
    elif data.video_number == 2:
        prompt_text = script.video2_prompt or ""
    else:
        prompt_text = script.video3_prompt or ""
    if not prompt_text:
        raise HTTPException(status_code=400, detail=f"No video{data.video_number}_prompt available. Generate prompts first.")

    # Get avatar image
    image_url = ""
    if data.avatar_id:
        avatar = db.query(Avatar).get(data.avatar_id)
        if avatar and avatar.image_url:
            image_url = avatar.image_url

    if not image_url:
        raise HTTPException(status_code=400, detail="Avatar image is required. Select an avatar with a generated image.")

    # Call Higgsfield
    result = generate_video(
        image_url=image_url,
        prompt=prompt_text,
        duration=data.duration,
        aspect_ratio=data.aspect_ratio,
        camera_movement=data.camera_movement,
        sound=data.sound,
        slow_motion=data.slow_motion,
        speed_ramp=data.speed_ramp,
        model_id=data.model_id,
    )

    # Save generation record
    gen = VideoGeneration(
        script_id=script_id,
        avatar_id=data.avatar_id,
        video_number=data.video_number,
        model_id=data.model_id,
        prompt=prompt_text,
        image_url=image_url,
        request_id=result.get("request_id", ""),
        status=result.get("status", "failed"),
        duration=data.duration,
        aspect_ratio=data.aspect_ratio,
        camera_movement=data.camera_movement,
        sound_enabled=data.sound,
        slow_motion=data.slow_motion,
        speed_ramp=data.speed_ramp,
        error_message=result.get("error", ""),
    )
    db.add(gen)
    db.commit()
    db.refresh(gen)

    return {"ok": True, "generation_id": gen.id, **result}


@router.get("/{script_id}/video-status/{generation_id}")
def video_status(script_id: int, generation_id: int, db: Session = Depends(get_db)):
    gen = db.query(VideoGeneration).get(generation_id)
    if not gen or gen.script_id != script_id:
        raise HTTPException(status_code=404, detail="Generation not found")

    if gen.status == "completed" and gen.video_url:
        return {
            "status": "completed",
            "video_url": gen.video_url,
            "subtitle_status": gen.subtitle_status or "",
        }

    if gen.status in ("failed", "nsfw", "cancelled"):
        return {"status": gen.status, "error": gen.error_message}

    if not gen.request_id:
        return {"status": "failed", "error": "No request ID"}

    result = hf_check_status(gen.request_id)
    if result["status"] == "completed":
        gen.status = "completed"
        gen.video_url = result.get("url", "")
        db.commit()
        # Auto-trigger subtitle generation for videos with sound
        if gen.video_url and gen.sound_enabled and not gen.subtitle_status:
            gen.subtitle_status = "processing"
            db.commit()
            _executor.submit(_add_subtitles_safe, gen.id)
        return {
            "status": "completed",
            "video_url": gen.video_url,
            "subtitle_status": gen.subtitle_status or "",
        }
    elif result["status"] in ("failed", "nsfw"):
        gen.status = result["status"]
        gen.error_message = result.get("error", "")
        db.commit()
        return {"status": gen.status, "error": gen.error_message}

    gen.status = result.get("status", "in_progress")
    db.commit()
    return {"status": gen.status}


@router.get("/{script_id}/video-generations")
def list_video_generations(script_id: int, db: Session = Depends(get_db)):
    gens = db.query(VideoGeneration).filter(
        VideoGeneration.script_id == script_id
    ).order_by(VideoGeneration.video_number, VideoGeneration.variant_index).all()
    return [
        {
            "id": g.id,
            "video_number": g.video_number,
            "variant_index": g.variant_index,
            "selected": g.selected,
            "model_id": g.model_id,
            "status": g.status,
            "video_url": g.video_url or "",
            "end_frame_url": g.end_frame_url or "",
            "duration": g.duration,
            "aspect_ratio": g.aspect_ratio,
            "sound_enabled": g.sound_enabled,
            "subtitle_status": g.subtitle_status or "",
            "subtitled_video_path": g.subtitled_video_path or "",
            "created_at": g.created_at.isoformat() if g.created_at else None,
        }
        for g in gens
    ]


@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if script:
        db.delete(script)
        db.commit()
    return {"ok": True}


# === Pipeline endpoints ===

@router.delete("/{script_id}/video-generation/{generation_id}")
def delete_generation(script_id: int, generation_id: int, db: Session = Depends(get_db)):
    gen = db.query(VideoGeneration).get(generation_id)
    if not gen or gen.script_id != script_id:
        raise HTTPException(status_code=404, detail="Generation not found")
    db.delete(gen)
    db.commit()
    return {"ok": True}


@router.post("/{script_id}/generate-step")
def generate_step(script_id: int, data: GenerateStepRequest, db: Session = Depends(get_db)):
    """Generate a pipeline step: 2 variants for the given video_number."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Get prompt text
    prompt_text = ""
    if data.video_number == 1:
        prompt_text = script.video1_prompt or ""
    elif data.video_number == 2:
        prompt_text = script.video2_prompt or ""
    else:
        prompt_text = script.video3_prompt or ""
    if not prompt_text:
        raise HTTPException(status_code=400, detail=f"No video{data.video_number}_prompt available.")

    # Get avatar image
    image_url = ""
    if data.avatar_id:
        avatar = db.query(Avatar).get(data.avatar_id)
        if avatar and avatar.image_url:
            image_url = avatar.image_url
    if not image_url:
        raise HTTPException(status_code=400, detail="Avatar image is required.")

    # If we have an end frame from previous step, use it as the start image
    start_image = data.end_frame_image or image_url

    generation_ids = []
    for variant_idx in range(2):
        result = generate_video(
            image_url=start_image,
            prompt=prompt_text,
            duration=data.duration,
            aspect_ratio=data.aspect_ratio,
            camera_movement=data.camera_movement,
            sound=data.sound,
            slow_motion=data.slow_motion,
            speed_ramp=data.speed_ramp,
            model_id=data.model_id,
        )
        gen = VideoGeneration(
            script_id=script_id,
            avatar_id=data.avatar_id,
            video_number=data.video_number,
            model_id=data.model_id,
            prompt=prompt_text,
            image_url=start_image,
            request_id=result.get("request_id", ""),
            status=result.get("status", "failed"),
            duration=data.duration,
            aspect_ratio=data.aspect_ratio,
            camera_movement=data.camera_movement,
            sound_enabled=data.sound,
            slow_motion=data.slow_motion,
            speed_ramp=data.speed_ramp,
            variant_index=variant_idx,
            error_message=result.get("error", ""),
        )
        db.add(gen)
        db.commit()
        db.refresh(gen)
        generation_ids.append(gen.id)

    return {"ok": True, "generation_ids": generation_ids}


@router.post("/{script_id}/select-variant")
def select_variant(script_id: int, data: SelectVariantRequest, db: Session = Depends(get_db)):
    """Select the winning variant for a pipeline step. Extracts end frame."""
    from services.video_utils import extract_last_frame

    gen = db.query(VideoGeneration).get(data.generation_id)
    if not gen or gen.script_id != script_id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if gen.status != "completed" or not gen.video_url:
        raise HTTPException(status_code=400, detail="Video not ready yet")

    # Mark this variant as selected
    gen.selected = True
    # Unselect other variants for this video_number
    others = db.query(VideoGeneration).filter(
        VideoGeneration.script_id == script_id,
        VideoGeneration.video_number == data.video_number,
        VideoGeneration.id != data.generation_id,
    ).all()
    for o in others:
        o.selected = False

    # Extract end frame for next step
    end_frame_url = ""
    try:
        end_frame_path = extract_last_frame(gen.video_url)
        # For serving locally, we need a static URL
        end_frame_url = f"/static/endframes/{os.path.basename(end_frame_path)}"
        # Move to static dir
        endframes_dir = os.path.join("static", "endframes")
        os.makedirs(endframes_dir, exist_ok=True)
        dest = os.path.join(endframes_dir, os.path.basename(end_frame_path))
        os.rename(end_frame_path, dest)
        gen.end_frame_url = end_frame_url
    except Exception as e:
        logger.error(f"End frame extraction failed: {e}")
        gen.end_frame_url = ""

    db.commit()
    return {
        "ok": True,
        "selected_id": gen.id,
        "end_frame_url": end_frame_url,
        "video_url": gen.video_url,
    }


@router.post("/{script_id}/concat-videos")
def concat_videos_endpoint(script_id: int, db: Session = Depends(get_db)):
    """Concatenate selected variants V1+V2+V3 and auto-generate subtitles."""
    from services.video_utils import concat_videos, download_video

    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Get selected variants in order
    selected = db.query(VideoGeneration).filter(
        VideoGeneration.script_id == script_id,
        VideoGeneration.selected == True,
    ).order_by(VideoGeneration.video_number).all()

    if not selected:
        raise HTTPException(status_code=400, detail="No variants selected. Select variants first.")

    # Download all videos locally
    downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    local_paths = []
    try:
        for gen in selected:
            if not gen.video_url:
                raise HTTPException(status_code=400, detail=f"Video {gen.video_number} has no URL")
            local_path = os.path.join(downloads_dir, f"concat_v{gen.video_number}_{script_id}.mp4")
            download_video(gen.video_url, local_path)
            local_paths.append(local_path)

        output_path = os.path.join(downloads_dir, f"final_{script_id}.mp4")
        concat_videos(local_paths, output_path)
        script.final_video_path = output_path
        db.commit()

        # Auto-trigger subtitle generation on the final video
        _executor.submit(_add_final_subtitles_safe, script_id)

        return {"ok": True, "final_video_path": output_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Concat failed for script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for p in local_paths:
            try:
                os.remove(p)
            except OSError:
                pass


def _validate_video_file(path: str) -> bool:
    """Check that a video file is valid (has moov atom) using ffprobe."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def _add_final_subtitles_safe(script_id: int):
    """Add subtitles to the final concatenated video using Whisper transcription."""
    from services.subtitler import _get_whisper_model, _burn_subtitles

    db = SessionLocal()
    try:
        script = db.query(Script).get(script_id)
        if not script or not script.final_video_path:
            return

        script.subtitle_status = "processing"
        script.subtitle_error = ""
        script.final_subtitled_path = ""
        db.commit()

        source_path = script.final_video_path

        # Validate video file before attempting subtitles
        if not os.path.exists(source_path) or not _validate_video_file(source_path):
            script.subtitle_status = "failed"
            script.subtitle_error = "Video file is invalid or incomplete (moov atom not found). Try re-processing the video."
            db.commit()
            logger.error(f"Video validation failed for script {script_id}: {source_path}")
            return
        downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
        audio_path = os.path.join(downloads_dir, f"final_{script_id}_audio.wav")
        output_path = os.path.join(downloads_dir, f"final_{script_id}_subtitled.mp4")

        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", source_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path
        ], check=True, capture_output=True)

        model = _get_whisper_model()
        result = model.transcribe(audio_path)
        timed_words = []
        for segment in result.segments:
            for word in segment.words:
                timed_words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                })

        if not timed_words:
            script.subtitle_status = "failed"
            script.subtitle_error = "No speech detected in video"
            db.commit()
            return

        _burn_subtitles(source_path, timed_words, output_path)

        script.final_subtitled_path = output_path
        script.subtitle_status = "completed"
        script.subtitle_error = ""
        db.commit()
        logger.info(f"Final subtitles completed for script {script_id}")

        try:
            os.remove(audio_path)
        except OSError:
            pass

    except Exception as e:
        logger.error(f"Final subtitles failed for script {script_id}: {e}")
        try:
            script = db.query(Script).get(script_id)
            if script:
                script.subtitle_status = "failed"
                script.subtitle_error = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/{script_id}/final-video-status")
def final_video_status(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {
        "final_video_path": script.final_video_path or "",
        "final_subtitled_path": script.final_subtitled_path or "",
        "has_final": bool(script.final_video_path),
        "has_subtitled": bool(script.final_subtitled_path),
        "subtitle_status": script.subtitle_status or "",
        "subtitle_error": script.subtitle_error or "",
        "has_raw_v1": bool(script.raw_video1_path and os.path.exists(script.raw_video1_path)),
        "has_raw_v2": bool(script.raw_video2_path and os.path.exists(script.raw_video2_path)),
    }


@router.get("/{script_id}/download-final")
def download_final(script_id: int, subtitled: bool = False, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    path = script.final_subtitled_path if subtitled else script.final_video_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Final video not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"script_{script_id}_final{'_subtitled' if subtitled else ''}.mp4",
        stat_result=os.stat(path),
    )


@router.post("/{script_id}/cancel-processing")
def cancel_processing(script_id: int, db: Session = Depends(get_db)):
    """Cancel any in-progress trim/subtitle processing."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if script.subtitle_status not in ("trimming", "processing"):
        return {"ok": True, "message": "Nothing to cancel"}
    script.subtitle_status = ""
    script.subtitle_error = ""
    db.commit()
    return {"ok": True, "message": "Processing cancelled"}


@router.post("/{script_id}/retry-subtitles")
def retry_subtitles(script_id: int, db: Session = Depends(get_db)):
    """Re-trigger subtitle generation on the final video."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if not script.final_video_path:
        raise HTTPException(status_code=400, detail="No final video to add subtitles to")
    if script.subtitle_status == "processing":
        return {"ok": True, "status": "processing", "message": "Already processing"}

    script.subtitle_status = "processing"
    script.subtitle_error = ""
    script.final_subtitled_path = ""
    db.commit()

    _executor.submit(_add_final_subtitles_safe, script_id)
    return {"ok": True, "status": "processing", "message": "Subtitle generation restarted"}


class TrimRequest(BaseModel):
    v1_start: float = 0
    v1_end: float = 0
    v2_start: float = 0
    v2_end: float = 0
    swap: bool = False


@router.post("/{script_id}/trim-concat")
def trim_concat(script_id: int, data: TrimRequest, db: Session = Depends(get_db)):
    """Trim raw videos at given times, concatenate in background."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    raw1 = script.raw_video1_path
    raw2 = script.raw_video2_path
    if not raw1 or not os.path.exists(raw1) or not raw2 or not os.path.exists(raw2):
        raise HTTPException(status_code=400, detail="Raw videos not available. Upload videos first.")

    # If swapped, flip the raw sources and trim params, and persist swap in DB
    if data.swap:
        raw1, raw2 = raw2, raw1
        data.v1_start, data.v2_start = data.v2_start, data.v1_start
        data.v1_end, data.v2_end = data.v2_end, data.v1_end
        script.raw_video1_path, script.raw_video2_path = raw1, raw2
        db.commit()

    # Mark as processing immediately and return
    script.subtitle_status = "trimming"
    db.commit()

    _executor.submit(
        _trim_concat_bg, script_id, raw1, raw2,
        data.v1_start, data.v1_end, data.v2_start, data.v2_end,
    )
    return {"ok": True, "status": "processing", "message": "Processing in background..."}


def _trim_concat_bg(script_id, raw1, raw2, v1_start, v1_end, v2_start, v2_end):
    """Background trim-concat worker."""
    import subprocess as sp
    from services.video_utils import concat_videos

    db = SessionLocal()
    downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
    trimmed_v1 = os.path.join(downloads_dir, f"trimmed_{script_id}_v1.mp4")
    trimmed_v2 = os.path.join(downloads_dir, f"trimmed_{script_id}_v2.mp4")
    output_path = os.path.join(downloads_dir, f"final_{script_id}.mp4")
    concat_ok = False

    try:
        cmd1 = ["ffmpeg", "-y", "-ss", str(v1_start), "-i", raw1]
        if v1_end > v1_start:
            cmd1 += ["-t", str(v1_end - v1_start)]
        cmd1 += ["-c", "copy", "-movflags", "+faststart", trimmed_v1]
        sp.run(cmd1, check=True, capture_output=True)

        cmd2 = ["ffmpeg", "-y", "-ss", str(v2_start), "-i", raw2]
        if v2_end > v2_start:
            cmd2 += ["-t", str(v2_end - v2_start)]
        cmd2 += ["-c", "copy", "-movflags", "+faststart", trimmed_v2]
        sp.run(cmd2, check=True, capture_output=True)

        concat_videos([trimmed_v1, trimmed_v2], output_path)

        script = db.query(Script).get(script_id)
        script.final_video_path = output_path
        script.final_subtitled_path = ""
        script.subtitle_status = "processing"
        script.subtitle_error = ""
        db.commit()
        logger.info(f"Trim-concat done for script {script_id}, starting subtitles...")
        concat_ok = True
    except Exception as e:
        concat_ok = False
        logger.error(f"Trim-concat failed for script {script_id}: {e}")
        try:
            script = db.query(Script).get(script_id)
            script.subtitle_status = ""
            script.subtitle_error = f"Trim failed: {e}"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
        for p in [trimmed_v1, trimmed_v2]:
            try:
                os.remove(p)
            except OSError:
                pass

    # Auto-trigger subtitles AFTER concat is fully done (file written + DB committed)
    if concat_ok:
        _add_final_subtitles_safe(script_id)


@router.get("/{script_id}/raw-video/{num}")
def get_raw_video(script_id: int, num: int, request: Request, db: Session = Depends(get_db)):
    """Serve raw video 1 or 2 for preview in trim editor (with Range support)."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if num == 1:
        path = script.raw_video1_path
    elif num == 2:
        path = script.raw_video2_path
    else:
        raise HTTPException(status_code=400, detail="num must be 1 or 2")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Raw video {num} not found")

    file_size = os.path.getsize(path)
    range_header = request.headers.get("range")

    if range_header:
        # Parse "bytes=start-end"
        range_str = range_header.replace("bytes=", "")
        parts = range_str.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        length = end - start + 1

        def iter_file():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
        )

    return FileResponse(path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})


@router.post("/{script_id}/upload-videos")
async def upload_videos(
    script_id: int,
    video1: UploadFile = File(...),
    video2: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload 2 video files, save raw copies, concatenate, and auto-add subtitles."""
    from services.video_utils import concat_videos
    import shutil

    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    v1_path = os.path.join(downloads_dir, f"upload_v1_{script_id}.mp4")
    v2_path = os.path.join(downloads_dir, f"upload_v2_{script_id}.mp4")
    raw_v1 = os.path.join(downloads_dir, f"raw_{script_id}_v1.mp4")
    raw_v2 = os.path.join(downloads_dir, f"raw_{script_id}_v2.mp4")
    output_path = os.path.join(downloads_dir, f"final_{script_id}.mp4")

    try:
        # Save uploaded files
        with open(v1_path, "wb") as f:
            content = await video1.read()
            f.write(content)
        with open(v2_path, "wb") as f:
            content = await video2.read()
            f.write(content)

        # Save raw copies for trim editor
        shutil.copy2(v1_path, raw_v1)
        shutil.copy2(v2_path, raw_v2)
        script.raw_video1_path = raw_v1
        script.raw_video2_path = raw_v2

        # Concatenate
        concat_videos([v1_path, v2_path], output_path)
        script.final_video_path = output_path
        script.final_subtitled_path = ""  # reset
        script.subtitle_status = ""
        script.subtitle_error = ""
        db.commit()

        return {"ok": True, "status": "uploaded", "message": "Videos concatenated. Use trim editor or add subtitles."}
    except Exception as e:
        logger.error(f"Upload + concat failed for script {script_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for p in [v1_path, v2_path]:
            try:
                os.remove(p)
            except OSError:
                pass


@router.post("/{script_id}/upload-single-video")
async def upload_single_video(
    script_id: int,
    video: UploadFile = File(...),
    num: int = Form(...),
    db: Session = Depends(get_db),
):
    """Upload a single replacement video (1 or 2)."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if num not in (1, 2):
        raise HTTPException(status_code=400, detail="num must be 1 or 2")

    downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    raw_path = os.path.join(downloads_dir, f"raw_{script_id}_v{num}.mp4")

    with open(raw_path, "wb") as f:
        content = await video.read()
        f.write(content)

    if num == 1:
        script.raw_video1_path = raw_path
    else:
        script.raw_video2_path = raw_path

    # Clear final video since it's now outdated
    for p in [script.final_video_path, script.final_subtitled_path]:
        if p:
            try:
                os.remove(p)
            except OSError:
                pass
    script.final_video_path = ""
    script.final_subtitled_path = ""
    script.subtitle_status = ""
    script.subtitle_error = ""
    db.commit()
    return {"ok": True, "message": f"Video {num} uploaded"}


@router.get("/{script_id}/thumbnail")
def get_thumbnail(script_id: int, db: Session = Depends(get_db)):
    """Extract and serve first frame of raw video 1 as a small JPEG thumbnail."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    # Prefer subtitled final, then raw_video1, then final_video
    src = script.final_subtitled_path or script.raw_video1_path or script.final_video_path
    if not src or not os.path.exists(src):
        raise HTTPException(status_code=404, detail="No video available")

    downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
    thumb_path = os.path.join(downloads_dir, f"thumb_{script_id}.jpg")

    # Generate thumbnail if not cached (or source video is newer)
    if not os.path.exists(thumb_path) or os.path.getmtime(src) > os.path.getmtime(thumb_path):
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-vframes", "1", "-vf", "scale=80:-1", "-q:v", "5", thumb_path],
            capture_output=True, timeout=10,
        )
    if not os.path.exists(thumb_path):
        raise HTTPException(status_code=404, detail="Thumbnail generation failed")

    return FileResponse(thumb_path, media_type="image/jpeg")


@router.delete("/{script_id}/raw-video/{num}")
def delete_raw_video(script_id: int, num: int, db: Session = Depends(get_db)):
    """Delete raw video 1 or 2 and its related final/subtitled files."""
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if num == 1:
        path = script.raw_video1_path
        script.raw_video1_path = ""
    elif num == 2:
        path = script.raw_video2_path
        script.raw_video2_path = ""
    else:
        raise HTTPException(status_code=400, detail="num must be 1 or 2")
    # Delete file from disk
    if path:
        try:
            os.remove(path)
        except OSError:
            pass
    # Also clear final video since it's now invalid
    for p in [script.final_video_path, script.final_subtitled_path]:
        if p:
            try:
                os.remove(p)
            except OSError:
                pass
    script.final_video_path = ""
    script.final_subtitled_path = ""
    script.subtitle_status = ""
    script.subtitle_error = ""
    db.commit()
    return {"ok": True, "message": f"Video {num} deleted"}


@router.post("/{script_id}/generate-metadata")
def generate_metadata(script_id: int, db: Session = Depends(get_db)):
    """Generate publication metadata (title, description, tags) per platform using Claude."""
    import anthropic
    from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    text = script.modified_text or script.original_text
    if not text:
        raise HTTPException(status_code=400, detail="No script text")

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are a social media expert. Given this video script, generate publication metadata for 3 platforms.

SCRIPT:
{text[:3000]}

Generate JSON with this exact structure (no markdown, just raw JSON):
{{
  "tiktok": {{
    "title": "short catchy title under 60 chars with hooks",
    "description": "2-3 sentences with emojis, call-to-action, under 150 chars",
    "tags": "#hashtag1 #hashtag2 #hashtag3 (10-15 relevant trending hashtags)"
  }},
  "instagram": {{
    "title": "catchy title under 60 chars",
    "description": "3-4 sentences with emojis, storytelling hook, call-to-action, under 300 chars",
    "tags": "#hashtag1 #hashtag2 (15-20 relevant hashtags)"
  }},
  "youtube": {{
    "title": "SEO-optimized title under 70 chars",
    "description": "5-7 sentences with SEO keywords, call-to-action, links placeholder, under 500 chars",
    "tags": "tag1, tag2, tag3 (10-15 comma-separated SEO tags)"
  }}
}}"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        raw = response.content[0].text.strip()
        # Try to extract JSON from response
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        script.pub_title_tiktok = data.get("tiktok", {}).get("title", "")
        script.pub_desc_tiktok = data.get("tiktok", {}).get("description", "")
        script.pub_tags_tiktok = data.get("tiktok", {}).get("tags", "")
        script.pub_title_instagram = data.get("instagram", {}).get("title", "")
        script.pub_desc_instagram = data.get("instagram", {}).get("description", "")
        script.pub_tags_instagram = data.get("instagram", {}).get("tags", "")
        script.pub_title_youtube = data.get("youtube", {}).get("title", "")
        script.pub_desc_youtube = data.get("youtube", {}).get("description", "")
        script.pub_tags_youtube = data.get("youtube", {}).get("tags", "")
        db.commit()

        return {"ok": True, "metadata": data}
    except json.JSONDecodeError as e:
        logger.error(f"Metadata JSON parse error: {e}, raw: {raw[:200]}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        logger.error(f"Metadata generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{script_id}/metadata")
def get_metadata(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {
        "tiktok": {
            "title": script.pub_title_tiktok or "",
            "description": script.pub_desc_tiktok or "",
            "tags": script.pub_tags_tiktok or "",
        },
        "instagram": {
            "title": script.pub_title_instagram or "",
            "description": script.pub_desc_instagram or "",
            "tags": script.pub_tags_instagram or "",
        },
        "youtube": {
            "title": script.pub_title_youtube or "",
            "description": script.pub_desc_youtube or "",
            "tags": script.pub_tags_youtube or "",
        },
    }


# === Subtitle endpoints ===

def _add_subtitles_safe(generation_id: int):
    """Wrapper for background subtitle generation."""
    try:
        add_subtitles(generation_id)
    except Exception as e:
        logger.error(f"Subtitle generation failed for gen {generation_id}: {e}")


@router.post("/{script_id}/add-subtitles/{generation_id}")
def add_subtitles_endpoint(script_id: int, generation_id: int, db: Session = Depends(get_db)):
    gen = db.query(VideoGeneration).get(generation_id)
    if not gen or gen.script_id != script_id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if gen.status != "completed" or not gen.video_url:
        raise HTTPException(status_code=400, detail="Video not ready yet")
    if gen.subtitle_status == "processing":
        return {"ok": True, "status": "processing", "message": "Already processing"}
    if gen.subtitle_status == "completed":
        return {"ok": True, "status": "completed", "message": "Subtitles already generated"}

    gen.subtitle_status = "processing"
    db.commit()
    _executor.submit(_add_subtitles_safe, gen.id)
    return {"ok": True, "status": "processing"}


@router.get("/{script_id}/subtitle-status/{generation_id}")
def subtitle_status(script_id: int, generation_id: int, db: Session = Depends(get_db)):
    gen = db.query(VideoGeneration).get(generation_id)
    if not gen or gen.script_id != script_id:
        raise HTTPException(status_code=404, detail="Generation not found")
    resp = {
        "subtitle_status": gen.subtitle_status or "",
        "subtitle_error": gen.subtitle_error or "",
    }
    if gen.subtitle_status == "completed" and gen.subtitled_video_path:
        resp["download_url"] = f"/api/scripts/{script_id}/download-subtitled/{generation_id}"
    return resp


@router.get("/{script_id}/download-subtitled/{generation_id}")
def download_subtitled(script_id: int, generation_id: int, db: Session = Depends(get_db)):
    gen = db.query(VideoGeneration).get(generation_id)
    if not gen or gen.script_id != script_id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if not gen.subtitled_video_path or not os.path.exists(gen.subtitled_video_path):
        raise HTTPException(status_code=404, detail="Subtitled video not found")
    return FileResponse(
        gen.subtitled_video_path,
        media_type="video/mp4",
        filename=f"script_{script_id}_gen_{generation_id}_subtitled.mp4",
    )
