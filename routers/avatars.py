import logging
from typing import Optional
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


def _avatar_to_dict(a: Avatar) -> dict:
    return {
        "id": a.id,
        "parent_id": a.parent_id,
        "name": a.name,
        "description": a.description or "",
        "prompt": a.prompt or "",
        "image_url": a.image_url or "",
        "image_request_id": a.image_request_id or "",
        "character_type": a.character_type or "",
        "variant_label": a.variant_label or "",
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/avatars", response_class=HTMLResponse)
def avatars_page(request: Request, db: Session = Depends(get_db)):
    # Only show root avatars (no parent) in the sidebar list
    avatars = db.query(Avatar).filter(Avatar.parent_id.is_(None)).order_by(Avatar.created_at.desc()).all()
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
        prompt=data.prompt or data.description,
    )
    db.add(avatar)
    db.commit()
    db.refresh(avatar)
    return {"ok": True, "id": avatar.id, "name": avatar.name}


class AvatarUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    character_type: Optional[str] = None
    prompt: Optional[str] = None


@router.put("/api/avatars/{avatar_id}")
def update_avatar(avatar_id: int, data: AvatarUpdate, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if data.name is not None:
        avatar.name = data.name
    if data.description is not None:
        avatar.description = data.description
    if data.character_type is not None:
        avatar.character_type = data.character_type
    if data.prompt is not None:
        avatar.prompt = data.prompt
    db.commit()
    return {"ok": True}


@router.get("/api/avatars")
def list_avatars(db: Session = Depends(get_db)):
    avatars = db.query(Avatar).filter(Avatar.parent_id.is_(None)).order_by(Avatar.created_at.desc()).all()
    return [_avatar_to_dict(a) for a in avatars]


@router.get("/api/avatars/{avatar_id}")
def get_avatar(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return _avatar_to_dict(avatar)


@router.get("/api/avatars/{avatar_id}/variants")
def get_variants(avatar_id: int, db: Session = Depends(get_db)):
    """Get all variants (children) of an avatar, including the parent itself."""
    parent = db.query(Avatar).get(avatar_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Avatar not found")
    # Return parent first, then variants sorted by creation
    variants = db.query(Avatar).filter(Avatar.parent_id == avatar_id).order_by(Avatar.created_at.asc()).all()
    return {
        "parent": _avatar_to_dict(parent),
        "variants": [_avatar_to_dict(v) for v in variants],
    }


class VariantRequest(BaseModel):
    mode: str  # "outfits" or "new_look"
    count: int = 3


@router.post("/api/avatars/{avatar_id}/generate-variants")
def generate_variants(avatar_id: int, data: VariantRequest, db: Session = Depends(get_db)):
    """Generate variant images for an avatar (new outfits or completely new looks)."""
    parent = db.query(Avatar).get(avatar_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Avatar not found")

    base_prompt = parent.prompt or parent.description
    if not base_prompt:
        raise HTTPException(status_code=400, detail="Avatar has no prompt for variant generation")

    count = min(data.count, 4)  # Max 4 variants at once
    variants_created = []

    for i in range(count):
        if data.mode == "outfits":
            variant_prompt = (
                f"{base_prompt}. "
                f"Same person, but wearing a completely different outfit #{i+1}. "
                f"Slightly different camera angle and pose. Different clothing style and colors."
            )
            label = f"outfit_{i+1}"
        else:  # new_look
            variant_prompt = (
                f"{base_prompt}. "
                f"Same person, but in a completely different location and environment #{i+1}. "
                f"Different outfit, different background, different lighting and mood. Fresh new scene."
            )
            label = f"new_look_{i+1}"

        # Create variant avatar
        variant = Avatar(
            parent_id=parent.id,
            name=f"{parent.name} — {label.replace('_', ' ').title()}",
            description=parent.description,
            prompt=variant_prompt,
            character_type=parent.character_type,
            variant_label=label,
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)

        # Start image generation
        result = generate_avatar_image(variant_prompt)
        if result.get("request_id"):
            variant.image_request_id = result["request_id"]
            db.commit()

        variants_created.append({
            "id": variant.id,
            "variant_label": label,
            "request_id": result.get("request_id", ""),
            "status": result.get("status", "failed"),
        })

    return {"ok": True, "variants": variants_created}


@router.post("/api/avatars/{avatar_id}/generate-image")
def generate_image(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    prompt = avatar.prompt or avatar.description
    if not prompt:
        raise HTTPException(status_code=400, detail="Avatar has no prompt or description for image generation")

    result = generate_avatar_image(prompt)
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
    # Delete all variants first
    db.query(Avatar).filter(Avatar.parent_id == avatar_id).delete()
    db.delete(avatar)
    db.commit()
    return {"ok": True}
