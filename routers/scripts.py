import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Video, Script
from services.pipeline import extract_script_for_video
from services.rewriter import rewrite_provocative
from services.classifier import classify_script
from services.scorer import score_viral_potential
from services.prompter import generate_video_prompt

router = APIRouter(prefix="/api/scripts", tags=["scripts"])
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=3)


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
        "status": script.status,
    }


VALID_ASSIGNEES = {"boris", "thomas", "daniel", ""}


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

    prompt = generate_video_prompt(text)
    script.video_prompt = prompt
    db.commit()
    return {"ok": True, "video_prompt": prompt}


@router.post("/batch-generate-prompts")
def batch_generate_prompts(db: Session = Depends(get_db)):
    """Generate video prompts for all assigned scripts that don't have one yet."""
    scripts = db.query(Script).filter(
        Script.assigned_to != "",
        Script.assigned_to.isnot(None),
        (Script.video_prompt == "") | (Script.video_prompt.is_(None)),
    ).all()
    count = 0
    errors = 0
    for script in scripts:
        text = script.modified_text or script.original_text
        if not text:
            continue
        try:
            prompt = generate_video_prompt(text)
            script.video_prompt = prompt
            db.commit()
            count += 1
            logger.info(f"Generated prompt for script #{script.id}")
        except Exception as e:
            errors += 1
            logger.error(f"Prompt generation failed for script #{script.id}: {e}")
    return {"ok": True, "generated": count, "errors": errors, "total_queued": len(scripts)}


@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if script:
        db.delete(script)
        db.commit()
    return {"ok": True}
