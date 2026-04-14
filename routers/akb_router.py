"""CRUD API for local AKB data tables."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import AkbClient, AkbMentor, AkbReview, AkbSuccessStory

router = APIRouter(prefix="/api/akb", tags=["akb"])


# ── Pydantic schemas ─────────────────────────────────────────────

class ClientIn(BaseModel):
    name: str
    mentor_name: str = ""
    responsible_name: str = ""
    status: str = ""
    tariff_type: str = ""
    tariff_price: float | None = None
    currency: str = "RUB"
    payment_method: str = ""
    product_type: str = ""
    target_country: str = ""
    target_year: int | None = None
    telegram: str = ""
    age: int | None = None
    last_payment_date: str = ""
    agreement_status: str = ""
    is_akb: bool = True
    is_archived: bool = False


class MentorIn(BaseModel):
    name: str
    university: str = ""
    degree: str = ""
    major: str = ""
    graduation_year: int | None = None
    specializations: list[str] = []
    countries: list[str] = []
    universities_expertise: list[str] = []
    students_helped: int = 0
    success_rate: float | None = None
    avg_scholarship_usd: int | None = None
    bio_short: str = ""
    mentor_type: str = ""
    track_type: str = ""
    is_active: bool = True
    is_paused: bool = False
    is_featured: bool = False
    email: str = ""


class ReviewIn(BaseModel):
    university: str = ""
    student_name: str = ""
    student_country: str = ""
    rating: int | None = None
    text: str = ""
    year: int | None = None
    is_verified: bool = False
    category: str = ""
    source: str = ""
    scholarship_amount: int | None = None
    offers_count: int | None = None
    mentor_name: str = ""
    program_level: str = ""


class StoryIn(BaseModel):
    student_name: str = ""
    student_country: str = ""
    university: str = ""
    program: str = ""
    degree: str = ""
    admission_year: int | None = None
    admission_type: str = ""
    scholarship_usd: int | None = None
    scholarship_percent: float | None = None
    financial_aid_total_usd: int | None = None
    story_short: str = ""
    story_full: str = ""
    quote: str = ""
    highlights: list[str] = []
    offers_received: int | None = None
    is_featured: bool = False
    is_verified: bool = False


# ── CLIENTS ───────────────────────────────────────────────────────

@router.post("/clients")
def create_client(data: ClientIn, db: Session = Depends(get_db)):
    obj = AkbClient(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id}


@router.put("/clients/{client_id}")
def update_client(client_id: int, data: ClientIn, db: Session = Depends(get_db)):
    obj = db.query(AkbClient).get(client_id)
    if not obj:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/clients/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    obj = db.query(AkbClient).get(client_id)
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ── MENTORS ───────────────────────────────────────────────────────

@router.post("/mentors")
def create_mentor(data: MentorIn, db: Session = Depends(get_db)):
    d = data.model_dump()
    d["specializations"] = json.dumps(d["specializations"])
    d["countries"] = json.dumps(d["countries"])
    d["universities_expertise"] = json.dumps(d["universities_expertise"])
    obj = AkbMentor(**d)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id}


@router.put("/mentors/{mentor_id}")
def update_mentor(mentor_id: int, data: MentorIn, db: Session = Depends(get_db)):
    obj = db.query(AkbMentor).get(mentor_id)
    if not obj:
        raise HTTPException(404)
    d = data.model_dump()
    d["specializations"] = json.dumps(d["specializations"])
    d["countries"] = json.dumps(d["countries"])
    d["universities_expertise"] = json.dumps(d["universities_expertise"])
    for k, v in d.items():
        setattr(obj, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/mentors/{mentor_id}")
def delete_mentor(mentor_id: int, db: Session = Depends(get_db)):
    obj = db.query(AkbMentor).get(mentor_id)
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ── REVIEWS ───────────────────────────────────────────────────────

@router.post("/reviews")
def create_review(data: ReviewIn, db: Session = Depends(get_db)):
    obj = AkbReview(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id}


@router.put("/reviews/{review_id}")
def update_review(review_id: int, data: ReviewIn, db: Session = Depends(get_db)):
    obj = db.query(AkbReview).get(review_id)
    if not obj:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    obj = db.query(AkbReview).get(review_id)
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ── SUCCESS STORIES ───────────────────────────────────────────────

@router.post("/stories")
def create_story(data: StoryIn, db: Session = Depends(get_db)):
    d = data.model_dump()
    d["highlights"] = json.dumps(d["highlights"])
    obj = AkbSuccessStory(**d)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id}


@router.put("/stories/{story_id}")
def update_story(story_id: int, data: StoryIn, db: Session = Depends(get_db)):
    obj = db.query(AkbSuccessStory).get(story_id)
    if not obj:
        raise HTTPException(404)
    d = data.model_dump()
    d["highlights"] = json.dumps(d["highlights"])
    for k, v in d.items():
        setattr(obj, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/stories/{story_id}")
def delete_story(story_id: int, db: Session = Depends(get_db)):
    obj = db.query(AkbSuccessStory).get(story_id)
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}
