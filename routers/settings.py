import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import ApiKey, ApiUsage, SystemPrompt

router = APIRouter(tags=["settings"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "active_page": "settings"}
    )


# --- API Key management ---

class ApiKeyCreate(BaseModel):
    platform: str
    label: str = ""
    key_value: str


@router.get("/api/settings/keys")
def list_keys(db: Session = Depends(get_db)):
    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return [
        {
            "id": k.id,
            "platform": k.platform,
            "label": k.label,
            "key_masked": k.key_value[:8] + "****" + k.key_value[-4:] if len(k.key_value) > 12 else "****",
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in keys
    ]


@router.post("/api/settings/keys")
def add_key(data: ApiKeyCreate, db: Session = Depends(get_db)):
    key = ApiKey(
        platform=data.platform,
        label=data.label,
        key_value=data.key_value,
        is_active=True,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return {"ok": True, "id": key.id}


@router.delete("/api/settings/keys/{key_id}")
def delete_key(key_id: int, db: Session = Depends(get_db)):
    key = db.query(ApiKey).get(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    db.delete(key)
    db.commit()
    return {"ok": True}


@router.put("/api/settings/keys/{key_id}/toggle")
def toggle_key(key_id: int, db: Session = Depends(get_db)):
    key = db.query(ApiKey).get(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = not key.is_active
    db.commit()
    return {"ok": True, "is_active": key.is_active}


# --- Usage stats ---

@router.get("/api/settings/usage")
def usage_stats(db: Session = Depends(get_db)):
    # Total by platform
    by_platform = (
        db.query(ApiUsage.platform, func.count(ApiUsage.id))
        .group_by(ApiUsage.platform)
        .all()
    )
    # By request_type
    by_type = (
        db.query(ApiUsage.platform, ApiUsage.request_type, func.count(ApiUsage.id))
        .group_by(ApiUsage.platform, ApiUsage.request_type)
        .all()
    )
    # By model
    by_model = (
        db.query(ApiUsage.platform, ApiUsage.model_id, func.count(ApiUsage.id))
        .filter(ApiUsage.model_id != "")
        .group_by(ApiUsage.platform, ApiUsage.model_id)
        .all()
    )
    # Total
    total = db.query(func.count(ApiUsage.id)).scalar()

    return {
        "total": total,
        "by_platform": {p: c for p, c in by_platform},
        "by_type": [{"platform": p, "type": t, "count": c} for p, t, c in by_type],
        "by_model": [{"platform": p, "model": m, "count": c} for p, m, c in by_model],
    }


# --- System Prompts ---

PROMPT_DEFAULTS = {
    "rewrite_system": None,
    "rewrite_user": None,
    "rewrite_boris_system": None,
    "rewrite_boris_user": None,
    "video1_system": None,
    "video1_user": None,
    "video2_system": None,
    "video2_user": None,
}


def _load_defaults():
    """Load hardcoded defaults from service files (lazy, once)."""
    if PROMPT_DEFAULTS["rewrite_system"] is not None:
        return
    from services.rewriter import SYSTEM_PROMPT, REWRITE_PROMPT, BORIS_SYSTEM_PROMPT, BORIS_REWRITE_PROMPT
    from services.prompter import SYSTEM_VIDEO1, USER_VIDEO1, SYSTEM_VIDEO2, USER_VIDEO2
    PROMPT_DEFAULTS["rewrite_system"] = SYSTEM_PROMPT
    PROMPT_DEFAULTS["rewrite_user"] = REWRITE_PROMPT
    PROMPT_DEFAULTS["rewrite_boris_system"] = BORIS_SYSTEM_PROMPT
    PROMPT_DEFAULTS["rewrite_boris_user"] = BORIS_REWRITE_PROMPT
    PROMPT_DEFAULTS["video1_system"] = SYSTEM_VIDEO1
    PROMPT_DEFAULTS["video1_user"] = USER_VIDEO1
    PROMPT_DEFAULTS["video2_system"] = SYSTEM_VIDEO2
    PROMPT_DEFAULTS["video2_user"] = USER_VIDEO2


PROMPT_LABELS = {
    "rewrite_system": "Rewrite — System Prompt",
    "rewrite_user": "Rewrite — User Prompt",
    "rewrite_boris_system": "Rewrite Boris — System Prompt",
    "rewrite_boris_user": "Rewrite Boris — User Prompt",
    "video1_system": "Video 1 — System Prompt",
    "video1_user": "Video 1 — User Template",
    "video2_system": "Video 2 — System Prompt",
    "video2_user": "Video 2 — User Template",
}


@router.get("/api/settings/prompts")
def list_prompts(db: Session = Depends(get_db)):
    _load_defaults()
    db_prompts = {p.key: p.value for p in db.query(SystemPrompt).all()}
    result = []
    for key in PROMPT_LABELS:
        result.append({
            "key": key,
            "label": PROMPT_LABELS[key],
            "value": db_prompts.get(key, PROMPT_DEFAULTS.get(key, "")),
            "is_custom": key in db_prompts,
        })
    return result


class PromptUpdate(BaseModel):
    value: str


@router.put("/api/settings/prompts/{key}")
def update_prompt(key: str, data: PromptUpdate, db: Session = Depends(get_db)):
    if key not in PROMPT_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown prompt key: {key}")
    row = db.query(SystemPrompt).filter(SystemPrompt.key == key).first()
    if row:
        row.value = data.value
    else:
        db.add(SystemPrompt(key=key, value=data.value))
    db.commit()
    return {"ok": True, "key": key}


@router.delete("/api/settings/prompts/{key}")
def reset_prompt(key: str, db: Session = Depends(get_db)):
    """Reset prompt to hardcoded default by deleting the DB override."""
    row = db.query(SystemPrompt).filter(SystemPrompt.key == key).first()
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True, "key": key, "reset": True}
