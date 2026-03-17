import logging
from datetime import date, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database import get_db
from models import VideoGeneration, Script, Video, Avatar

router = APIRouter(tags=["videos"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

CREATORS = ["daniel", "boris", "thomas"]
# Default publication offsets from TikTok date
PUB_OFFSETS = {"tiktok": 0, "instagram": 7, "youtube": 14}


@router.get("/videos", response_class=HTMLResponse)
def videos_page(request: Request, db: Session = Depends(get_db)):
    generations = (
        db.query(VideoGeneration)
        .options(
            joinedload(VideoGeneration.script).joinedload(Script.video),
            joinedload(VideoGeneration.avatar),
        )
        .order_by(VideoGeneration.created_at.desc())
        .all()
    )

    # Build schedule: per-creator scripts with video generations
    schedule = {}
    for creator in CREATORS:
        scripts = (
            db.query(Script)
            .options(joinedload(Script.video))
            .filter(Script.assigned_to == creator)
            .order_by(Script.id.desc())
            .all()
        )
        # Get generation counts per script
        gen_counts = {}
        completed_counts = {}
        for s in scripts:
            gens = db.query(VideoGeneration).filter(VideoGeneration.script_id == s.id).all()
            gen_counts[s.id] = len(gens)
            completed_counts[s.id] = len([g for g in gens if g.status == "completed"])

        # Get final video URLs per script
        final_videos = {}
        for s in scripts:
            if s.final_subtitled_path:
                final_videos[s.id] = f"/api/scripts/{s.id}/download-final?subtitled=true"
            elif s.final_video_path:
                final_videos[s.id] = f"/api/scripts/{s.id}/download-final"

        schedule[creator] = {
            "scripts": scripts,
            "gen_counts": gen_counts,
            "completed_counts": completed_counts,
            "final_videos": final_videos,
        }

    return templates.TemplateResponse(
        "videos.html",
        {
            "request": request,
            "active_page": "videos",
            "generations": generations,
            "schedule": schedule,
            "creators": CREATORS,
            "pub_offsets": PUB_OFFSETS,
        }
    )
