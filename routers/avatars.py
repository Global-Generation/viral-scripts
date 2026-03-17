import logging
import os
import uuid
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Avatar
from services.higgsfield import (
    generate_avatar_image, check_status,
    create_soul_id, check_soul_id_status, generate_with_soul_id,
)

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
        "soul_id": a.soul_id or "",
        "soul_id_status": a.soul_id_status or "",
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

    # Auto-heal stuck variants: have request_id but no image_url (e.g. after deploy/restart)
    for v in variants:
        if v.image_request_id and not v.image_url:
            try:
                result = check_status(v.image_request_id)
                if result["status"] == "completed" and result.get("url"):
                    v.image_url = result["url"]
                    db.commit()
                    logger.info(f"Auto-healed stuck variant {v.id}")
            except Exception as e:
                logger.warning(f"Auto-heal check failed for variant {v.id}: {e}")

    # Also check parent if stuck
    if parent.image_request_id and not parent.image_url:
        try:
            result = check_status(parent.image_request_id)
            if result["status"] == "completed" and result.get("url"):
                parent.image_url = result["url"]
                db.commit()
                logger.info(f"Auto-healed stuck parent avatar {parent.id}")
        except Exception as e:
            logger.warning(f"Auto-heal check failed for parent {parent.id}: {e}")

    return {
        "parent": _avatar_to_dict(parent),
        "variants": [_avatar_to_dict(v) for v in variants],
    }


class VariantRequest(BaseModel):
    mode: str  # "outfits", "new_look", or "location"
    count: int = 3


class CustomVariantRequest(BaseModel):
    prompt: str


# Lightweight base for all variant prompts — mode-specific logic adds the rest
PORTRAIT_BASE = (
    "Vertical photo (9:16). Photorealistic, high detail. "
    "No phone, no selfie. "
)


# UGC base prefix for all avatar image prompts
UGC_PREFIX = (
    "Vertical photo (9:16). Webcam-style framing at desk distance. "
    "Person occupies lower 60% of frame, head at upper third — leaving generous space above for the room environment. "
    "Visible from chest/torso up, one hand gesturing with a pen. Sitting in a leather chair at a wooden desk. "
    "Looking directly at camera with confident eye contact. Front-facing, slightly below eye level. "
    "IMPORTANT: background takes up at least 40% of the image. "
    "Background must be sharp, detailed, and richly decorated — bookshelves with books, framed diplomas and certificates on walls, "
    "table lamp with warm glow, framed photos, wooden paneling. Deep depth of field, nothing blurred. "
    "Photorealistic, high detail. No phone, no selfie. "
)


@router.post("/api/avatars/{avatar_id}/generate-variants")
def generate_variants(avatar_id: int, data: VariantRequest, db: Session = Depends(get_db)):
    """Generate variant images using image-to-image to preserve face."""
    parent = db.query(Avatar).get(avatar_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Avatar not found")

    if not parent.image_url:
        raise HTTPException(status_code=400, detail="Avatar must have a generated image first")

    # Auto-train Soul ID if not started yet (once)
    if not parent.soul_id:
        image_urls = [parent.image_url]
        variants_with_img = db.query(Avatar).filter(
            Avatar.parent_id == avatar_id,
            Avatar.image_url != "",
            Avatar.image_url.isnot(None),
        ).all()
        for v in variants_with_img:
            if v.image_url:
                image_urls.append(v.image_url)
        soul_result = create_soul_id(name=parent.name, image_urls=image_urls)
        if soul_result.get("soul_id"):
            parent.soul_id = soul_result["soul_id"]
            parent.soul_id_status = "training"
            db.commit()
        return {"ok": True, "status": "training_started",
                "message": "Soul ID training started. Wait 3-5 minutes, then try again."}

    # Check if Soul ID is still training
    if parent.soul_id_status == "training":
        soul_check = check_soul_id_status(parent.soul_id)
        if soul_check["status"] == "ready":
            parent.soul_id_status = "ready"
            db.commit()
        elif soul_check["status"] == "failed":
            parent.soul_id_status = "failed"
            db.commit()
            return {"ok": False, "status": "soul_failed", "message": "Soul ID training failed. Try again."}
        else:
            return {"ok": True, "status": "training",
                    "message": "Soul ID still training. Please wait..."}

    base_prompt = parent.prompt or parent.description
    if not base_prompt:
        raise HTTPException(status_code=400, detail="Avatar has no prompt for variant generation")

    # Outfit styles to cycle through for variety
    OUTFIT_OPTIONS = [
        "wearing a formal navy blazer with light blue dress shirt",
        "wearing a casual hoodie and t-shirt",
        "wearing a leather jacket with dark turtleneck",
        "wearing a classic gray suit with white shirt and tie",
    ]
    LOCATION_OPTIONS = [
        "in a modern office with bookshelves and warm lighting",
        "in a cozy cafe with soft ambient lighting",
        "in a bright studio with white background",
        "outdoors on a city street with buildings behind",
    ]

    count = min(data.count, 4)
    variants_created = []

    # Step 1: Build all variant prompts and save to DB
    # NOTE: Soul ID preserves the face. Prompts must NOT re-describe the person's
    # appearance — that conflicts with Soul ID and distorts the face. Only describe
    # what should CHANGE (outfit, location) and tell it to keep everything else.
    variant_records = []
    for i in range(count):
        if data.mode == "outfits":
            outfit = OUTFIT_OPTIONS[i % len(OUTFIT_OPTIONS)]
            variant_prompt = (
                f"{PORTRAIT_BASE}"
                f"Same person from reference image, {outfit}. "
                f"Keep the same face, background, and setting. Only change the clothes."
            )
            label = f"outfit_{i+1}"
        elif data.mode == "location":
            location = LOCATION_OPTIONS[i % len(LOCATION_OPTIONS)]
            variant_prompt = (
                f"{PORTRAIT_BASE}"
                f"Same person from reference image, same outfit and clothes. "
                f"New setting: {location}."
            )
            label = f"location_{i+1}"
        else:  # new_look
            outfit = OUTFIT_OPTIONS[i % len(OUTFIT_OPTIONS)]
            location = LOCATION_OPTIONS[i % len(LOCATION_OPTIONS)]
            variant_prompt = (
                f"{PORTRAIT_BASE}"
                f"Same person from reference image, {outfit}. "
                f"Setting: {location}."
            )
            label = f"new_look_{i+1}"

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
        variant_records.append((variant, variant_prompt, label))

    # Step 2: Submit all generation requests in parallel
    import concurrent.futures

    def _submit_one(soul_id, prompt):
        result = generate_with_soul_id(soul_id=soul_id, prompt=prompt)
        if not result.get("request_id"):
            import time
            time.sleep(2)
            result = generate_with_soul_id(soul_id=soul_id, prompt=prompt)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_submit_one, parent.soul_id, vp)
            for _, vp, _ in variant_records
        ]
        results = [f.result() for f in futures]

    for (variant, _, label), result in zip(variant_records, results):
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


@router.post("/api/avatars/{avatar_id}/generate-custom-variant")
def generate_custom_variant(avatar_id: int, data: CustomVariantRequest, db: Session = Depends(get_db)):
    """Generate a single custom variant using user-provided text."""
    parent = db.query(Avatar).get(avatar_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if not parent.image_url:
        raise HTTPException(status_code=400, detail="Avatar must have a generated image first")

    # Auto-train Soul ID if not started yet
    if not parent.soul_id:
        image_urls = [parent.image_url]
        variants_with_img = db.query(Avatar).filter(
            Avatar.parent_id == avatar_id,
            Avatar.image_url != "",
            Avatar.image_url.isnot(None),
        ).all()
        for v in variants_with_img:
            if v.image_url:
                image_urls.append(v.image_url)
        soul_result = create_soul_id(name=parent.name, image_urls=image_urls)
        if soul_result.get("soul_id"):
            parent.soul_id = soul_result["soul_id"]
            parent.soul_id_status = "training"
            db.commit()
        return {"ok": True, "status": "training_started",
                "message": "Soul ID training started. Wait 3-5 minutes, then try again."}

    # Check if Soul ID is still training
    if parent.soul_id_status == "training":
        soul_check = check_soul_id_status(parent.soul_id)
        if soul_check["status"] == "ready":
            parent.soul_id_status = "ready"
            db.commit()
        elif soul_check["status"] == "failed":
            parent.soul_id_status = "failed"
            db.commit()
            return {"ok": False, "status": "soul_failed", "message": "Soul ID training failed. Try again."}
        else:
            return {"ok": True, "status": "training",
                    "message": "Soul ID still training. Please wait..."}

    base_prompt = parent.prompt or parent.description
    if not base_prompt:
        raise HTTPException(status_code=400, detail="Avatar has no prompt for variant generation")

    # Count existing custom variants to number the label
    existing_custom = db.query(Avatar).filter(
        Avatar.parent_id == avatar_id,
        Avatar.variant_label.like("custom_%"),
    ).count()
    label = f"custom_{existing_custom + 1}"

    variant_prompt = (
        f"{PORTRAIT_BASE}"
        f"Same person from reference image. "
        f"Keep the same face, background, outfit, and pose. "
        f"Only apply this change: {data.prompt}"
    )

    variant = Avatar(
        parent_id=parent.id,
        name=f"{parent.name} — Custom",
        description=parent.description,
        prompt=variant_prompt,
        character_type=parent.character_type,
        variant_label=label,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    result = generate_with_soul_id(soul_id=parent.soul_id, prompt=variant_prompt)
    if not result.get("request_id"):
        import time
        time.sleep(2)
        result = generate_with_soul_id(soul_id=parent.soul_id, prompt=variant_prompt)

    if result.get("request_id"):
        variant.image_request_id = result["request_id"]
        db.commit()

    return {
        "ok": True,
        "id": variant.id,
        "request_id": result.get("request_id", ""),
        "status": result.get("status", "submitted"),
    }


@router.post("/api/avatars/{avatar_id}/generate-image")
def generate_image(avatar_id: int, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    prompt = avatar.prompt or avatar.description
    if not prompt:
        raise HTTPException(status_code=400, detail="Avatar has no prompt or description for image generation")

    # Add UGC-style prefix for vertical phone selfie format
    full_prompt = f"{UGC_PREFIX}{prompt}"
    result = generate_avatar_image(full_prompt)
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

        # Auto-start Soul ID training as soon as first image is ready
        if not avatar.soul_id and avatar.image_url and not avatar.parent_id:
            try:
                soul_result = create_soul_id(name=avatar.name, image_urls=[avatar.image_url])
                if soul_result.get("soul_id"):
                    avatar.soul_id = soul_result["soul_id"]
                    avatar.soul_id_status = "training"
                    db.commit()
                    logger.info(f"Auto-started Soul ID training for avatar {avatar.id}")
            except Exception as e:
                logger.error(f"Auto Soul ID training failed: {e}")

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


class UploadUrlRequest(BaseModel):
    image_url: str


@router.post("/api/avatars/{avatar_id}/upload-url")
def upload_avatar_url(avatar_id: int, data: UploadUrlRequest, db: Session = Depends(get_db)):
    """Set avatar image from an external URL (e.g. Higgsfield CDN link)."""
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    avatar.image_url = data.image_url
    db.commit()
    return {"ok": True, "image_url": avatar.image_url}


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")


@router.post("/api/avatars/{avatar_id}/upload-image")
async def upload_avatar_image(avatar_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a local image file as avatar photo."""
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")

    ext = os.path.splitext(file.filename or "img.png")[1] or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(UPLOAD_DIR, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    avatar.image_url = f"/static/uploads/{filename}"
    db.commit()
    return {"ok": True, "image_url": avatar.image_url}


# === Soul ID ===

@router.post("/api/avatars/{avatar_id}/train-soul")
def train_soul_id(avatar_id: int, db: Session = Depends(get_db)):
    """Train a Soul ID for perfect face preservation in variants."""
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if not avatar.image_url:
        raise HTTPException(status_code=400, detail="Avatar must have an image first")
    if avatar.soul_id and avatar.soul_id_status == "ready":
        return {"ok": True, "soul_id": avatar.soul_id, "status": "ready"}

    # Collect all available images: parent + all variant images
    image_urls = [avatar.image_url]
    variants = db.query(Avatar).filter(
        Avatar.parent_id == avatar_id,
        Avatar.image_url != "",
        Avatar.image_url.isnot(None),
    ).all()
    for v in variants:
        if v.image_url:
            image_urls.append(v.image_url)

    result = create_soul_id(name=avatar.name, image_urls=image_urls)
    if result.get("soul_id"):
        avatar.soul_id = result["soul_id"]
        avatar.soul_id_status = "training"
        db.commit()
        return {"ok": True, "soul_id": result["soul_id"], "status": "training",
                "images_used": len(image_urls)}
    else:
        return {"ok": False, "error": result.get("error", "Unknown error")}


@router.get("/api/avatars/{avatar_id}/soul-status")
def soul_status(avatar_id: int, db: Session = Depends(get_db)):
    """Check Soul ID training status."""
    avatar = db.query(Avatar).get(avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if not avatar.soul_id:
        return {"status": "none"}
    if avatar.soul_id_status == "ready":
        return {"status": "ready", "soul_id": avatar.soul_id}

    result = check_soul_id_status(avatar.soul_id)
    if result["status"] == "ready":
        avatar.soul_id_status = "ready"
        db.commit()
    elif result["status"] == "failed":
        avatar.soul_id_status = "failed"
        db.commit()
    return result
