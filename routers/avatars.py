import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Avatar
from services.higgsfield import generate_avatar_image, check_status

router = APIRouter(tags=["avatars"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/avatars", response_class=HTMLResponse)
def avatars_page(request: Request, db: Session = Depends(get_db)):
    avatars = db.query(Avatar).order_by(Avatar.created_at.desc()).all()
    return templates.TemplateResponse(
        "avatars.html",
        {"request": request, "active_page": "avatars", "avatars": avatars}
    )


class AvatarCreate(BaseModel):
    name: str
    description: str = ""
    character_type: str = ""
    prompt: str = ""


@router.post("/api/avatars")
def create_avatar(data: AvatarCreate, db: Session = Depends(get_db)):
    avatar = Avatar(
        name=data.name,
        description=data.description,
        character_type=data.character_type,
        prompt=data.prompt,
    )
    db.add(avatar)
    db.commit()
    db.refresh(avatar)
    return {
        "ok": True,
        "id": avatar.id,
        "name": avatar.name,
    }


@router.get("/api/avatars")
def list_avatars(db: Session = Depends(get_db)):
    avatars = db.query(Avatar).order_by(Avatar.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "prompt": a.prompt,
            "image_url": a.image_url or "",
            "image_request_id": a.image_request_id or "",
            "character_type": a.character_type or "",
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in avatars
    ]


@router.post("/api/avatars/{avatar_id}/generate-image")
def generate_image(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if not avatar.prompt:
        raise HTTPException(status_code=400, detail="Avatar has no prompt for image generation")

    result = generate_avatar_image(avatar.prompt)
    if result.get("request_id"):
        avatar.image_request_id = result["request_id"]
        db.commit()
    return {"ok": True, **result}


@router.get("/api/avatars/{avatar_id}/status")
def avatar_status(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")

    if not avatar.image_request_id:
        return {"status": "no_request", "image_url": avatar.image_url or ""}

    if avatar.image_url:
        return {"status": "completed", "image_url": avatar.image_url}

    result = check_status(avatar.image_request_id)
    if result["status"] == "completed":
        avatar.image_url = result.get("url", "")
        db.commit()
        return {"status": "completed", "image_url": avatar.image_url}

    return result


@router.delete("/api/avatars/{avatar_id}")
def delete_avatar(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    db.delete(avatar)
    db.commit()
    return {"ok": True}
