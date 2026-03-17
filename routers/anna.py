from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import AnnaVideo
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/anna", response_class=HTMLResponse)
def anna_page(request: Request, db: Session = Depends(get_db)):
    videos = db.query(AnnaVideo).order_by(AnnaVideo.id).all()
    return templates.TemplateResponse(
        "anna.html",
        {"request": request, "active_page": "anna", "videos": videos}
    )


class DateUpdate(BaseModel):
    platform: str
    date: Optional[str] = ""


@router.post("/api/anna/{video_id}/publish-date")
def anna_publish_date(video_id: int, data: DateUpdate, db: Session = Depends(get_db)):
    video = db.query(AnnaVideo).get(video_id)
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


@router.post("/api/anna/{video_id}/production")
def anna_production(video_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    video = db.query(AnnaVideo).get(video_id)
    if not video:
        return JSONResponse({"error": "Not found"}, 404)
    video.production_status = data.production_status
    db.commit()
    return {"ok": True}
