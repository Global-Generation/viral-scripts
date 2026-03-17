from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Script, Video, Search

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CHARACTERS = {
    "boris": {"label": "AI - Boris", "color": "#2563EB"},
    "daniel": {"label": "AI - Daniel", "color": "#ea580c"},
    "thomas": {"label": "AI - Thomas", "color": "#16a34a"},
}


@router.get("/character/{name}", response_class=HTMLResponse)
def character_page(name: str, request: Request, db: Session = Depends(get_db)):
    if name not in CHARACTERS:
        return HTMLResponse("Character not found", status_code=404)
    info = CHARACTERS[name]
    scripts = (
        db.query(Script)
        .join(Video)
        .join(Search, Video.search_id == Search.id)
        .filter(Script.assigned_to == name)
        .order_by(Script.viral_score.desc(), Script.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "character.html",
        {
            "request": request,
            "active_page": f"char_{name}",
            "name": name,
            "label": info["label"],
            "color": info["color"],
            "scripts": scripts,
        }
    )
