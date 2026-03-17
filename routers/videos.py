import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import VideoGeneration, Script, Video, Avatar

router = APIRouter(tags=["videos"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


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
    return templates.TemplateResponse(
        "videos.html",
        {"request": request, "active_page": "videos", "generations": generations}
    )
