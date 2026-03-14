from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import PresetQuery

router = APIRouter(prefix="/api/presets", tags=["presets"])


class PresetCreate(BaseModel):
    category: str
    query: str


@router.get("")
def list_presets(db: Session = Depends(get_db)):
    presets = db.query(PresetQuery).order_by(PresetQuery.category, PresetQuery.sort_order).all()
    return [{"id": p.id, "category": p.category, "query": p.query} for p in presets]


@router.post("")
def create_preset(data: PresetCreate, db: Session = Depends(get_db)):
    preset = PresetQuery(category=data.category, query=data.query)
    db.add(preset)
    db.commit()
    return {"id": preset.id}


@router.delete("/{preset_id}")
def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.query(PresetQuery).get(preset_id)
    if preset:
        db.delete(preset)
        db.commit()
    return {"ok": True}
