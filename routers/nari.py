import json
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from collections import defaultdict
from database import get_db
from models import NariVideo
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/nari", response_class=HTMLResponse)
def nari_page(request: Request, db: Session = Depends(get_db)):
    videos = db.query(NariVideo).order_by(NariVideo.id).all()
    day_map = defaultdict(lambda: {"tiktok": 0, "instagram": 0, "youtube": 0})
    for v in videos:
        if v.published_tiktok:
            day_map[v.published_tiktok.strftime("%Y-%m-%d")]["tiktok"] += 1
        if v.published_instagram:
            day_map[v.published_instagram.strftime("%Y-%m-%d")]["instagram"] += 1
        if v.published_youtube:
            day_map[v.published_youtube.strftime("%Y-%m-%d")]["youtube"] += 1
    timeline = [{"date": d, **counts} for d, counts in sorted(day_map.items())]
    total_videos = len(videos)
    pub_tt = sum(1 for v in videos if v.published_tiktok)
    pub_ig = sum(1 for v in videos if v.published_instagram)
    pub_yt = sum(1 for v in videos if v.published_youtube)
    ready_videos = sum(1 for v in videos if v.production_status in ("ready", "filmed", "published"))
    photos_dir = os.path.join("static", "photos", "nari")
    total_photos = len([f for f in os.listdir(photos_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]) if os.path.isdir(photos_dir) else 0
    return templates.TemplateResponse(
        "nari.html",
        {"request": request, "active_page": "nari", "videos": videos,
         "total_videos": total_videos, "total_photos": total_photos,
         "ready_videos": ready_videos, "pub_tt": pub_tt, "pub_ig": pub_ig, "pub_yt": pub_yt,
         "timeline_json": json.dumps(timeline)}
    )


class DateUpdate(BaseModel):
    platform: str
    date: Optional[str] = ""


@router.post("/api/nari/{video_id}/publish-date")
def nari_publish_date(video_id: int, data: DateUpdate, db: Session = Depends(get_db)):
    video = db.query(NariVideo).get(video_id)
    if not video:
        return JSONResponse({"error": "Not found"}, 404)
    dt = datetime.strptime(data.date, "%Y-%m-%d") if data.date else None
    field = f"published_{data.platform}"
    if hasattr(video, field):
        setattr(video, field, dt)
        db.commit()
    return {"ok": True}


class TogglePublish(BaseModel):
    platform: str = "tiktok"


@router.post("/api/nari/{video_id}/toggle-publish")
def nari_toggle_publish(video_id: int, data: TogglePublish, db: Session = Depends(get_db)):
    video = db.query(NariVideo).get(video_id)
    if not video:
        return JSONResponse({"error": "Not found"}, 404)
    field = f"published_{data.platform}"
    if not hasattr(video, field):
        return JSONResponse({"error": "Invalid platform"}, 400)
    current = getattr(video, field)
    if current:
        setattr(video, field, None)
        db.commit()
        return {"ok": True, "published": False}
    else:
        setattr(video, field, datetime.now(timezone.utc))
        db.commit()
        return {"ok": True, "published": True}


class StatusUpdate(BaseModel):
    production_status: str = ""


@router.post("/api/nari/{video_id}/production")
def nari_production(video_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    video = db.query(NariVideo).get(video_id)
    if not video:
        return JSONResponse({"error": "Not found"}, 404)
    video.production_status = data.production_status
    db.commit()
    return {"ok": True}
