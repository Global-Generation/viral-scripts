"""AKB local data — reads from local SQLite tables (copy-paste from Mentorship-AKB)."""
import json
import logging

logger = logging.getLogger(__name__)


def _safe_json(val):
    """Parse JSON column value, return list or original."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


def get_clients(db, limit: int = 200) -> list[dict]:
    from models import AkbClient
    rows = db.query(AkbClient).filter(
        (AkbClient.is_archived == False) | (AkbClient.is_archived.is_(None))
    ).order_by(AkbClient.created_at.desc()).limit(limit).all()
    return [
        {
            "name": r.name, "telegram": r.telegram,
            "mentor_name": r.mentor_name, "responsible_name": r.responsible_name,
            "tariff_type": r.tariff_type, "tariff_price": r.tariff_price,
            "currency": r.currency, "status": r.status,
            "agreement_status": r.agreement_status,
            "target_country": r.target_country, "target_year": r.target_year,
            "last_payment_date": r.last_payment_date,
        }
        for r in rows
    ]


def get_reviews(db, limit: int = 100) -> list[dict]:
    from models import AkbReview
    rows = db.query(AkbReview).order_by(AkbReview.created_at.desc()).limit(limit).all()
    return [
        {
            "student_name": r.student_name, "student_country": r.student_country,
            "university": r.university, "rating": r.rating, "text": r.text,
            "year": r.year, "is_verified": r.is_verified,
            "category": r.category, "scholarship_amount": r.scholarship_amount,
            "mentor_name": r.mentor_name,
        }
        for r in rows
    ]


def get_success_stories(db, limit: int = 100) -> list[dict]:
    from models import AkbSuccessStory
    rows = (
        db.query(AkbSuccessStory)
        .order_by(AkbSuccessStory.is_featured.desc(), AkbSuccessStory.admission_year.desc())
        .limit(limit).all()
    )
    return [
        {
            "student_name": r.student_name, "student_country": r.student_country,
            "university": r.university, "program": r.program, "degree": r.degree,
            "admission_year": r.admission_year, "admission_type": r.admission_type,
            "scholarship_usd": r.scholarship_usd, "scholarship_percent": r.scholarship_percent,
            "financial_aid_total_usd": r.financial_aid_total_usd,
            "story_short": r.story_short, "quote": r.quote,
            "highlights": _safe_json(r.highlights),
            "offers_received": r.offers_received,
            "is_featured": r.is_featured, "is_verified": r.is_verified,
        }
        for r in rows
    ]


def get_mentors(db, limit: int = 100) -> list[dict]:
    from models import AkbMentor
    rows = (
        db.query(AkbMentor)
        .order_by(AkbMentor.is_featured.desc(), AkbMentor.students_helped.desc())
        .limit(limit).all()
    )
    return [
        {
            "name": r.name, "university": r.university, "degree": r.degree,
            "major": r.major, "graduation_year": r.graduation_year,
            "specializations": _safe_json(r.specializations),
            "countries": _safe_json(r.countries),
            "universities_expertise": _safe_json(r.universities_expertise),
            "students_helped": r.students_helped, "success_rate": r.success_rate,
            "avg_scholarship_usd": r.avg_scholarship_usd, "bio_short": r.bio_short,
            "mentor_type": r.mentor_type, "track_type": r.track_type,
            "is_active": r.is_active, "is_paused": r.is_paused,
            "is_featured": r.is_featured, "email": r.email,
        }
        for r in rows
    ]


def get_sales_stats(db) -> dict:
    from models import AkbClient
    total = db.query(AkbClient).count()
    active = db.query(AkbClient).filter(
        AkbClient.status.notin_(["churned", "lost"]),
        (AkbClient.is_archived == False) | (AkbClient.is_archived.is_(None))
    ).count()
    return {"total_clients": total, "active_clients": active}
