import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Video, Script
from services.pipeline import extract_script_for_video
from services.rewriter import rewrite_provocative

router = APIRouter(prefix="/api/scripts", tags=["scripts"])
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1)


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
        "status": script.status,
    }


class ScriptUpdate(BaseModel):
    original_text: str = None
    modified_text: str = None


@router.put("/{script_id}")
def update_script(script_id: int, data: ScriptUpdate, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if data.original_text is not None:
        script.original_text = data.original_text
    if data.modified_text is not None:
        script.modified_text = data.modified_text
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


@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if script:
        db.delete(script)
        db.commit()
    return {"ok": True}
