import json
import os
from collections import defaultdict
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Script, Video, Search

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CHARACTERS = {
    "boris": {"label": "AI - Boris", "color": "#2563EB"},
    "daniel": {"label": "AI - Daniel", "color": "#ea580c"},
    "thomas": {"label": "AI - Thomas", "color": "#16a34a"},
    "zoe": {"label": "AI - Zoe", "color": "#a855f7"},
    "natalie": {"label": "AI - Natalie", "color": "#ec4899"},
    "luna": {"label": "AI - Luna", "color": "#14b8a6"},
}


@router.get("/character/{name}", response_class=HTMLResponse)
def character_page(name: str, request: Request, db: Session = Depends(get_db)):
    if name not in CHARACTERS:
        return HTMLResponse("Character not found", status_code=404)
    info = CHARACTERS[name]
    scripts = (
        db.query(Script)
        .options(joinedload(Script.video).joinedload(Video.search))
        .filter(Script.assigned_to == name)
        .all()
    )

    # Sort by production readiness (most complete first)
    def status_order(s):
        if s.published_tiktok or s.published_instagram or s.published_youtube:
            return 7
        if s.final_subtitled_path:
            return 6
        if s.subtitle_status == "processing":
            return 5
        if s.subtitle_status == "failed":
            return 4
        if s.final_video_path:
            return 3
        if s.raw_video1_path or s.raw_video2_path:
            return 2
        if s.modified_text:
            return 1
        return 0

    scripts.sort(key=lambda s: (-status_order(s), -(s.viral_score or 0)))

    # --- Stats ---
    total = len(scripts)
    pub_tt = sum(1 for s in scripts if s.published_tiktok)
    pub_ig = sum(1 for s in scripts if s.published_instagram)
    pub_yt = sum(1 for s in scripts if s.published_youtube)

    ai_count = 0
    finance_count = 0
    score_sum = 0
    score_n = 0
    for s in scripts:
        cat = (s.video.search.category or "").lower() if s.video and s.video.search else ""
        if cat == "ai":
            ai_count += 1
        elif cat == "finance":
            finance_count += 1
        if s.viral_score and s.viral_score > 0:
            score_sum += s.viral_score
            score_n += 1
    avg_score = round(score_sum / score_n) if score_n else 0

    # Timeline: aggregate publish dates by day
    day_map = defaultdict(lambda: {"tiktok": 0, "instagram": 0, "youtube": 0})
    for s in scripts:
        if s.published_tiktok:
            day_map[s.published_tiktok.strftime("%Y-%m-%d")]["tiktok"] += 1
        if s.published_instagram:
            day_map[s.published_instagram.strftime("%Y-%m-%d")]["instagram"] += 1
        if s.published_youtube:
            day_map[s.published_youtube.strftime("%Y-%m-%d")]["youtube"] += 1
    timeline = [
        {"date": d, **counts}
        for d, counts in sorted(day_map.items())
    ]

    # Scan for character photos
    photos_dir = os.path.join("static", "photos", name)
    photos = []
    if os.path.isdir(photos_dir):
        photos = sorted(
            f for f in os.listdir(photos_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        )

    return templates.TemplateResponse(
        "character.html",
        {
            "request": request,
            "active_page": f"char_{name}",
            "name": name,
            "label": info["label"],
            "color": info["color"],
            "scripts": scripts,
            "total": total,
            "pub_tt": pub_tt,
            "pub_ig": pub_ig,
            "pub_yt": pub_yt,
            "ai_count": ai_count,
            "finance_count": finance_count,
            "avg_score": avg_score,
            "timeline_json": json.dumps(timeline),
            "photos": photos,
        }
    )
