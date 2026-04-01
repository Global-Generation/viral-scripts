import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Search, Video, Script, PresetQuery, VideoGeneration, TiktokStatsLog, TiktokStats

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
    return templates.TemplateResponse(
        "dashboard.html",
        ctx(request, "dashboard",
            recent_searches=recent_searches,
            ai_presets=ai_presets,
            finance_presets=finance_presets)
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
    db: Session = Depends(get_db)
):
    # Scripts Library shows only unassigned scripts
    # Assigned scripts (boris/daniel/thomas) have their own tabs
    base_q = (
        db.query(Script)
        .join(Video)
        .join(Search, Video.search_id == Search.id)
        .filter((Script.assigned_to == "") | (Script.assigned_to.is_(None)))
    )
    if category:
        base_q = base_q.filter(Search.category == category)

    q = base_q.order_by(Script.viral_score.desc(), Script.created_at.desc())
    scripts = q.all()
    return templates.TemplateResponse(
        "scripts_library.html",
        ctx(request, "scripts", scripts=scripts, category=category)
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


@router.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, db: Session = Depends(get_db)):
    from routers.character import CHARACTERS

    creators = ["daniel", "natalie", "boris", "thomas", "zoe", "luna", "sophia", "ava"]
    now = datetime.utcnow()  # naive UTC to match SQLite
    cutoff_30d = now - timedelta(days=30)

    # Get all log entries for last 30 days
    logs = (
        db.query(TiktokStatsLog)
        .filter(TiktokStatsLog.logged_at >= cutoff_30d)
        .order_by(TiktokStatsLog.logged_at.asc())
        .all()
    )

    # Group by creator → sorted list of entries
    by_creator: dict[str, list] = defaultdict(list)
    for log in logs:
        by_creator[log.creator].append(log)

    # Build per-creator stats with deltas
    creator_stats = []
    total_followers = 0
    total_hearts = 0
    total_videos = 0
    total_f_7d = 0
    total_f_30d = 0

    for c in creators:
        entries = by_creator.get(c, [])
        if not entries:
            creator_stats.append({
                "name": c,
                "label": CHARACTERS.get(c, {}).get("label", c),
                "color": CHARACTERS.get(c, {}).get("color", "#6b7280"),
                "followers": 0, "hearts": 0, "videos": 0,
                "d1_f": 0, "d7_f": 0, "d30_f": 0, "d7_h": 0,
            })
            continue

        latest = entries[-1]
        total_followers += latest.followers
        total_hearts += latest.hearts
        total_videos += latest.videos

        # Find entry closest to 1d, 7d, 30d ago
        def find_past(days):
            target = now - timedelta(days=days)
            best = None
            for e in entries:
                if e.logged_at <= target:
                    best = e
            return best

        e_1d = find_past(1)
        e_7d = find_past(7)
        e_30d = find_past(30) or (entries[0] if entries else None)

        d1_f = (latest.followers - e_1d.followers) if e_1d else 0
        d7_f = (latest.followers - e_7d.followers) if e_7d else 0
        d30_f = (latest.followers - e_30d.followers) if e_30d else 0
        d7_h = (latest.hearts - e_7d.hearts) if e_7d else 0

        total_f_7d += d7_f
        total_f_30d += d30_f

        creator_stats.append({
            "name": c,
            "label": CHARACTERS.get(c, {}).get("label", c),
            "color": CHARACTERS.get(c, {}).get("color", "#6b7280"),
            "followers": latest.followers,
            "hearts": latest.hearts,
            "videos": latest.videos,
            "d1_f": d1_f, "d7_f": d7_f, "d30_f": d30_f, "d7_h": d7_h,
        })

    # Views from cached video stats
    total_views = 0
    video_rows = db.query(TiktokStats).filter(TiktokStats.stat_type == "videos").all()
    views_by_creator = {}
    for row in video_rows:
        vids = json.loads(row.data) if row.data else []
        v = sum(v.get("views", 0) for v in vids) if isinstance(vids, list) else 0
        views_by_creator[row.creator] = v
        total_views += v
    for s in creator_stats:
        s["views"] = views_by_creator.get(s["name"], 0)

    # Last updated time in New York
    from zoneinfo import ZoneInfo
    latest_profile = db.query(func.max(TiktokStats.updated_at)).filter(TiktokStats.stat_type == "profile").scalar()
    if latest_profile:
        if latest_profile.tzinfo is None:
            latest_profile = latest_profile.replace(tzinfo=timezone.utc)
        ny_time = latest_profile.astimezone(ZoneInfo("America/New_York"))
        last_updated_ny = ny_time.strftime("%b %d, %Y %I:%M %p ET")
    else:
        last_updated_ny = "—"

    # Chart data: daily followers per creator (last 30 days)
    chart_data = {}
    for c in creators:
        entries = by_creator.get(c, [])
        chart_data[c] = [
            {"date": e.logged_at.strftime("%Y-%m-%d"), "followers": e.followers}
            for e in entries
        ]

    return templates.TemplateResponse(
        "stats.html",
        ctx(
            request, "stats",
            creator_stats=creator_stats,
            total_followers=total_followers,
            total_hearts=total_hearts,
            total_videos=total_videos,
            total_views=total_views,
            total_f_7d=total_f_7d,
            total_f_30d=total_f_30d,
            chart_data_json=json.dumps(chart_data),
            creators=creators,
            last_updated_ny=last_updated_ny,
        )
    )
