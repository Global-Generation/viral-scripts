from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from collections import defaultdict
from database import get_db
from models import NariVideo
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import json

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
    return templates.TemplateResponse(
        "nari.html",
        {"request": request, "active_page": "nari", "videos": videos,
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
