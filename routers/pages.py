from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Search, Video, Script, PresetQuery

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def ctx(request: Request, active_page: str, **extra):
    return {"request": request, "active_page": active_page, **extra}


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    recent_searches = (
        db.query(Search).order_by(Search.created_at.desc()).limit(10).all()
    )
    ai_presets = (
        db.query(PresetQuery)
        .filter(PresetQuery.category == "ai")
        .order_by(PresetQuery.sort_order)
        .all()
    )
    finance_presets = (
        db.query(PresetQuery)
        .filter(PresetQuery.category == "finance")
        .order_by(PresetQuery.sort_order)
        .all()
    )
    admissions_presets = (
        db.query(PresetQuery)
        .filter(PresetQuery.category == "admissions")
        .order_by(PresetQuery.sort_order)
        .all()
    )
    exams_presets = (
        db.query(PresetQuery)
        .filter(PresetQuery.category == "exams")
        .order_by(PresetQuery.sort_order)
        .all()
    )
    return templates.TemplateResponse(
        "dashboard.html",
        ctx(request, "dashboard",
            recent_searches=recent_searches,
            ai_presets=ai_presets,
            finance_presets=finance_presets,
            admissions_presets=admissions_presets,
            exams_presets=exams_presets)
    )


@router.get("/search", response_class=HTMLResponse)
def search_results_page(
    request: Request,
    search_id: int = Query(None),
    db: Session = Depends(get_db)
):
    if not search_id:
        return RedirectResponse("/")
    search = db.query(Search).get(search_id)
    if not search:
        return HTMLResponse("Search not found", status_code=404)
    videos = (
        db.query(Video)
        .filter(Video.search_id == search_id)
        .order_by(Video.score.desc())
        .all()
    )
    return templates.TemplateResponse(
        "search_results.html",
        ctx(request, "search", search=search, videos=videos)
    )


@router.get("/scripts", response_class=HTMLResponse)
def scripts_library(
    request: Request,
    category: str = Query(""),
    assigned: str = Query(""),
    db: Session = Depends(get_db)
):
    base_q = (
        db.query(Script)
        .join(Video)
        .join(Search, Video.search_id == Search.id)
    )
    if category:
        base_q = base_q.filter(Search.category == category)

    # Compute counts respecting category filter
    boris_count = base_q.filter(Script.assigned_to == "boris").count()
    thomas_count = base_q.filter(Script.assigned_to == "thomas").count()
    daniel_count = base_q.filter(Script.assigned_to == "daniel").count()
    assigned_count = boris_count + thomas_count + daniel_count
    total_count = base_q.count()
    unassigned_count = total_count - assigned_count

    # Apply assignment filter
    q = base_q.order_by(Script.viral_score.desc(), Script.created_at.desc())
    if assigned == "yes":
        q = q.filter(Script.assigned_to != "", Script.assigned_to.isnot(None))
    elif assigned == "no":
        q = q.filter((Script.assigned_to == "") | (Script.assigned_to.is_(None)))
    elif assigned in ("boris", "thomas", "daniel"):
        q = q.filter(Script.assigned_to == assigned)
    scripts = q.all()
    return templates.TemplateResponse(
        "scripts_library.html",
        ctx(request, "scripts", scripts=scripts, category=category, assigned=assigned,
            boris_count=boris_count, thomas_count=thomas_count, daniel_count=daniel_count,
            assigned_count=assigned_count, unassigned_count=unassigned_count)
    )


@router.get("/scripts/{script_id}", response_class=HTMLResponse)
def script_view(script_id: int, request: Request, db: Session = Depends(get_db)):
    script = db.query(Script).get(script_id)
    if not script:
        return HTMLResponse("Script not found", status_code=404)
    video = db.query(Video).get(script.video_id)
    search = db.query(Search).get(video.search_id) if video else None
    return templates.TemplateResponse(
        "script_view.html",
        ctx(request, "scripts", script=script, video=video, search=search)
    )


@router.get("/presets", response_class=HTMLResponse)
def presets_page(request: Request, db: Session = Depends(get_db)):
    presets = (
        db.query(PresetQuery)
        .order_by(PresetQuery.category, PresetQuery.sort_order)
        .all()
    )
    grouped = {
        "ai": [p for p in presets if p.category == "ai"],
        "finance": [p for p in presets if p.category == "finance"],
    }
    return templates.TemplateResponse(
        "presets.html",
        ctx(request, "presets", grouped=grouped)
    )
