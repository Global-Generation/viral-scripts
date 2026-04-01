import json
import logging
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Script, Video, Search, TiktokStats, TiktokStatsLog

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CHARACTERS = {
    "daniel": {
        "label": "AI - Daniel",
        "color": "#ea580c",
        "tiktok": "https://www.tiktok.com/@daniel.foster476",
        "bio": "\U0001f916 AI Finance & Lifestyle Creator\n\U0001f4b0 Smarter money moves, daily tips & real talk\n\U0001f4f2 MyTruv App Ambassador\n\U0001f34e Download MyTruv on the App Store",
    },
    "natalie": {
        "label": "AI - Natalie",
        "color": "#ec4899",
        "tiktok": "https://www.tiktok.com/@natalie.greene7",
        "bio": "\U0001f916 AI Personal Finance Creator\n\U0001f4b8 Building wealth in the age of AI\n\U0001f4f2 Powered by @MyTruv\n\U0001f34e Download MyTruv on the App Store",
    },
    "boris": {
        "label": "AI - Boris",
        "color": "#2563EB",
        "tiktok": "https://www.tiktok.com/@boris.johnson365",
        "bio": "\U0001f916 AI Tools & Money Creator\n\U0001f6e0\ufe0f Automation \u00b7 Side hustles \u00b7 Financial hacks\n\U0001f4f2 MyTruv App Ambassador\n\U0001f34e Download MyTruv on the App Store",
    },
    "thomas": {
        "label": "AI - Thomas",
        "color": "#16a34a",
        "tiktok": "https://www.tiktok.com/@thomas.foust2",
        "bio": "\U0001f916 AI Crypto & Wealth Creator\n\U0001f4c8 Trading, markets & wealth mentality\n\U0001f4f2 Ambassador @MyTruv\n\U0001f34e Download MyTruv on the App Store",
    },
    "zoe": {
        "label": "AI - Zoe",
        "color": "#a855f7",
        "tiktok": "https://www.tiktok.com/@zoe.carter855",
        "bio": "\U0001f916 AI Tech & Finance Creator\n\u26a1 Tech trends \u00b7 Crypto \u00b7 Financial freedom\n\U0001f4f2 MyTruv Ambassador\n\U0001f34e Download MyTruv on the App Store",
    },
    "luna": {
        "label": "AI - Luna",
        "color": "#14b8a6",
        "tiktok": "https://www.tiktok.com/@luna.bennett38",
        "bio": "\U0001f916 AI Passive Income Creator\n\U0001f319 Monetize AI, invest smart, earn while you sleep\n\U0001f4f2 Brought to you by @MyTruv\n\U0001f34e Download MyTruv on the App Store",
    },
    "sophia": {
        "label": "AI - Sophia",
        "color": "#9333ea",
        "tiktok": "https://www.tiktok.com/@sophia.alvarez.nyc",
        "bio": "",
    },
    "ava": {
        "label": "AI - Ava",
        "color": "#db2777",
        "tiktok": "https://www.tiktok.com/@ava.reynolds.newjersey",
        "bio": "",
    },
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
        if s.published_tiktok:
            return 3  # Published
        if s.final_subtitled_path or s.final_video_path:
            return 2  # Video Ready
        if s.modified_text:
            return 1  # Script Ready
        return 0  # Draft

    scripts.sort(key=lambda s: (-status_order(s), -(s.viral_score or 0)))

    # --- Stats ---
    total = len(scripts)
    pub_tt = sum(1 for s in scripts if s.published_tiktok)
    pub_ig = sum(1 for s in scripts if s.published_instagram)
    pub_yt = sum(1 for s in scripts if s.published_youtube)
    ready_videos = sum(1 for s in scripts if s.final_video_path or s.final_subtitled_path)

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

    # TikTok stats from cache
    profile_row = db.query(TiktokStats).filter(
        TiktokStats.creator == name, TiktokStats.stat_type == "profile"
    ).first()
    videos_row = db.query(TiktokStats).filter(
        TiktokStats.creator == name, TiktokStats.stat_type == "videos"
    ).first()
    tt_profile = json.loads(profile_row.data) if profile_row else None
    tt_videos = json.loads(videos_row.data) if videos_row else None
    tt_updated = profile_row.updated_at.strftime("%Y-%m-%d %H:%M") if profile_row and profile_row.updated_at else None

    return templates.TemplateResponse(
        "character.html",
        {
            "request": request,
            "active_page": f"char_{name}",
            "name": name,
            "label": info["label"],
            "color": info["color"],
            "bio": info.get("bio", ""),
            "tiktok": info.get("tiktok", ""),
            "scripts": scripts,
            "total": total,
            "pub_tt": pub_tt,
            "pub_ig": pub_ig,
            "pub_yt": pub_yt,
            "ai_count": ai_count,
            "finance_count": finance_count,
            "avg_score": avg_score,
            "ready_videos": ready_videos,
            "total_photos": len(photos),
            "timeline_json": json.dumps(timeline),
            "photos": photos,
            "tt_profile": tt_profile,
            "tt_videos": tt_videos,
            "tt_videos_json": json.dumps(tt_videos or []),
            "tt_updated": tt_updated,
        }
    )


@router.post("/api/character/{name}/refresh-tiktok")
def refresh_tiktok(name: str, db: Session = Depends(get_db)):
    if name not in CHARACTERS:
        return JSONResponse({"ok": False, "error": "Character not found"}, status_code=404)
    tiktok_url = CHARACTERS[name].get("tiktok", "")
    if not tiktok_url:
        return JSONResponse({"ok": False, "error": "No TikTok URL configured"}, status_code=400)

    from services.tiktok_stats import fetch_profile_stats, fetch_video_stats

    profile = fetch_profile_stats(tiktok_url)
    videos = fetch_video_stats(tiktok_url)
    now = datetime.now(timezone.utc)

    if profile:
        row = db.query(TiktokStats).filter(
            TiktokStats.creator == name, TiktokStats.stat_type == "profile"
        ).first()
        if row:
            row.data = json.dumps(profile)
            row.updated_at = now
        else:
            db.add(TiktokStats(creator=name, stat_type="profile", data=json.dumps(profile), updated_at=now))

    if videos is not None:
        row = db.query(TiktokStats).filter(
            TiktokStats.creator == name, TiktokStats.stat_type == "videos"
        ).first()
        if row:
            row.data = json.dumps(videos)
            row.updated_at = now
        else:
            db.add(TiktokStats(creator=name, stat_type="videos", data=json.dumps(videos), updated_at=now))

    db.commit()
    logger.info(f"Refreshed TikTok stats for {name}: profile={'yes' if profile else 'no'}, videos={len(videos) if videos else 0}")

    return {
        "ok": True,
        "profile": profile,
        "videos": videos,
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    }


@router.post("/api/tiktok/refresh-all")
def refresh_all_tiktok(db: Session = Depends(get_db)):
    from services.tiktok_stats import fetch_profile_stats, fetch_video_stats

    now = datetime.now(timezone.utc)
    results = {}
    errors = []

    for name, info in CHARACTERS.items():
        tiktok_url = info.get("tiktok", "")
        if not tiktok_url:
            continue
        profile = fetch_profile_stats(tiktok_url)
        if profile:
            # Update profile cache
            row = db.query(TiktokStats).filter(
                TiktokStats.creator == name, TiktokStats.stat_type == "profile"
            ).first()
            if row:
                row.data = json.dumps(profile)
                row.updated_at = now
            else:
                db.add(TiktokStats(creator=name, stat_type="profile", data=json.dumps(profile), updated_at=now))
            # Log for history
            db.add(TiktokStatsLog(
                creator=name,
                followers=profile.get("followers", 0),
                hearts=profile.get("hearts", 0),
                videos=profile.get("videos", 0),
                following=profile.get("following", 0),
                logged_at=now,
            ))
            profile["updated_at"] = now.strftime("%Y-%m-%d %H:%M")

            # Fetch and cache video stats (views)
            videos = fetch_video_stats(tiktok_url)
            if videos is not None:
                vrow = db.query(TiktokStats).filter(
                    TiktokStats.creator == name, TiktokStats.stat_type == "videos"
                ).first()
                if vrow:
                    vrow.data = json.dumps(videos)
                    vrow.updated_at = now
                else:
                    db.add(TiktokStats(creator=name, stat_type="videos", data=json.dumps(videos), updated_at=now))
                profile["views"] = sum(v.get("views", 0) for v in videos)
            else:
                profile["views"] = 0

            results[name] = profile
        else:
            errors.append(name)

    db.commit()
    logger.info(f"Refreshed all TikTok stats: {len(results)} ok, {len(errors)} failed")
    return {"ok": True, "stats": results, "errors": errors}


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/api/character/{name}/upload-photo")
async def upload_character_photo(name: str, file: UploadFile = File(...)):
    if name not in CHARACTERS:
        return JSONResponse({"ok": False, "error": "Character not found"}, status_code=404)

    ext = os.path.splitext(file.filename or "img.jpg")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse({"ok": False, "error": "Only JPG, PNG, WebP allowed"}, status_code=400)

    photos_dir = os.path.join("static", "photos", name)
    os.makedirs(photos_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(photos_dir, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    return {"ok": True, "filename": filename, "url": f"/static/photos/{name}/{filename}"}


@router.delete("/api/character/{name}/photo/{filename}")
async def delete_character_photo(name: str, filename: str):
    if name not in CHARACTERS:
        return JSONResponse({"ok": False, "error": "Character not found"}, status_code=404)

    filepath = os.path.join("static", "photos", name, filename)
    if not os.path.isfile(filepath):
        return JSONResponse({"ok": False, "error": "Photo not found"}, status_code=404)

    os.remove(filepath)
    return {"ok": True}
