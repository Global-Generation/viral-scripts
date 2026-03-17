import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import ApiKey, ApiUsage

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
