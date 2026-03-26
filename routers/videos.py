import logging
import os
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Script, Video, NariVideo, AnnaVideo

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "photos")

# US Eastern = UTC-4 (EDT) / UTC-5 (EST). Using EDT for now.
EDT = timezone(timedelta(hours=-4))

router = APIRouter(tags=["videos"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

CREATORS = ["sophia", "ava", "daniel", "boris", "thomas", "zoe", "natalie", "luna"]

# Per-creator start dates
SCHEDULE_STARTS = {
    "daniel":  date(2026, 3, 25),
    "boris":   date(2026, 3, 26),
    "thomas":  date(2026, 3, 26),
    "zoe":     date(2026, 3, 27),
    "natalie": date(2026, 3, 27),
    "luna":    date(2026, 3, 28),
    "sophia":  date(2026, 3, 16),
    "ava":     date(2026, 3, 16),
}


def _script_status(script):
    """Return (status_label, status_color) for a script."""
    if script.published_tiktok:
        return "Published", "#16a34a"
    if script.final_subtitled_path and os.path.isfile(script.final_subtitled_path):
        return "Subtitled", "#0891b2"
    if script.subtitle_status == "processing":
        return "Adding Subs", "#8b5cf6"
    if script.final_video_path and os.path.isfile(script.final_video_path):
        return "Video Ready", "#2563eb"
    if (script.raw_video1_path and os.path.isfile(script.raw_video1_path)) or \
       (script.raw_video2_path and os.path.isfile(script.raw_video2_path)):
        return "Filmed", "#ca8a04"
    if script.modified_text:
        return "Script Only", "#9ca3af"
    return "Draft", "#d1d5db"


def _build_script_schedule(db, creator, today):
    """Build schedule for script-based creators (daniel, boris, thomas)."""
    scripts = (
        db.query(Script)
        .options(joinedload(Script.video))
        .filter(Script.assigned_to == creator)
        .order_by(Script.id.asc())
        .all()
    )

    # Self-healing: clear DB paths for deleted video files
    dirty = False
    for s in scripts:
        for attr in ("final_subtitled_path", "final_video_path", "raw_video1_path", "raw_video2_path"):
            path = getattr(s, attr)
            if path and not os.path.isfile(path):
                setattr(s, attr, None)
                dirty = True
    if dirty:
        db.commit()

    # Sort: ready (has final video) first, then by id
    def _readiness(s):
        if s.final_subtitled_path:
            return 0
        if s.final_video_path:
            return 1
        if s.raw_video1_path or s.raw_video2_path:
            return 2
        return 3
    scripts.sort(key=lambda s: (_readiness(s), s.id))

    start = SCHEDULE_STARTS[creator]
    entries = []
    tasks = []
    for i, script in enumerate(scripts):
        base_date = start + timedelta(days=i // 2)
        slot = "morning" if i % 2 == 0 else "evening"
        tt_date = base_date

        s_label, s_color = _script_status(script)
        title = script.pub_title_tiktok or (script.video.title if script.video else None) or f"Script #{script.id}"
        entries.append({
            "title": title[:55],
            "link": f"/scripts/{script.id}",
            "script_id": script.id,
            "has_raw_video": bool(script.raw_video1_path or script.final_video_path),
            "tiktok_date": tt_date,
            "has_final": bool(script.final_video_path or script.final_subtitled_path),
            "slot": slot,
            "published_tiktok": bool(script.published_tiktok),
            "status": s_label,
            "status_color": s_color,
        })

        if tt_date == today:
            tasks.append({
                "creator": creator,
                "title": title[:60],
                "link": f"/scripts/{script.id}",
                "platform": "TikTok",
                "date": tt_date,
                "slot": slot,
                "script_id": script.id,
                "publish_url": f"/api/scripts/{script.id}/publish",
                "published": bool(script.published_tiktok),
                "status": s_label,
                "status_color": s_color,
            })

    # Published to bottom of the table
    entries.sort(key=lambda e: (1 if e["published_tiktok"] else 0))

    return entries, tasks


def _build_nari_schedule(db, today):
    """Build schedule for Sophia (NariVideo).
    Published videos use actual pub dates; unpublished start from today at 2/day.
    """
    videos = db.query(NariVideo).order_by(NariVideo.id.asc()).all()

    published = [v for v in videos if v.published_tiktok]
    unpublished = [v for v in videos if not v.published_tiktok]
    published.sort(key=lambda v: v.published_tiktok)

    entries = []
    tasks = []

    # Published videos → actual dates
    date_slots = {}
    for v in published:
        tt_date = v.published_tiktok.date() if hasattr(v.published_tiktok, 'date') else v.published_tiktok
        slot_n = date_slots.get(tt_date, 0)
        slot = "morning" if slot_n % 2 == 0 else "evening"
        date_slots[tt_date] = slot_n + 1

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/nari",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "has_final": True,
            "slot": slot,
            "published_tiktok": True,
            "status": "Published",
            "status_color": "#16a34a",
        })
        if tt_date == today:
            tasks.append({
                "creator": "sophia",
                "title": v.title[:60] if v.title else f"Video #{v.id}",
                "link": "/nari",
                "platform": "TikTok",
                "date": tt_date,
                "slot": slot,
                "script_id": None,
                "publish_url": f"/api/nari/{v.id}/toggle-publish",
                "published": True,
                "has_final": True,
                "status": "Published",
                "status_color": "#16a34a",
            })

    # Unpublished videos → fill from next slot after last published
    if date_slots:
        last_pub_date = max(date_slots.keys())
        slots_on_last = date_slots[last_pub_date]
    else:
        last_pub_date = SCHEDULE_STARTS.get("sophia", today)
        slots_on_last = 0
    for i, v in enumerate(unpublished):
        adj_i = i + slots_on_last
        base_date = last_pub_date + timedelta(days=adj_i // 2)
        slot = "morning" if adj_i % 2 == 0 else "evening"
        tt_date = base_date
        is_ready = v.production_status in ("ready", "published")
        status = "Video Ready" if is_ready else "Draft"
        status_color = "#2563eb" if is_ready else "#d1d5db"

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/nari",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "has_final": is_ready,
            "slot": slot,
            "published_tiktok": False,
            "status": status,
            "status_color": status_color,
        })
        if tt_date == today:
            tasks.append({
                "creator": "sophia",
                "title": v.title[:60] if v.title else f"Video #{v.id}",
                "link": "/nari",
                "platform": "TikTok",
                "date": tt_date,
                "slot": slot,
                "script_id": None,
                "publish_url": f"/api/nari/{v.id}/toggle-publish",
                "published": False,
                "has_final": is_ready,
                "status": status,
                "status_color": status_color,
            })

    # Published to bottom of the table
    entries.sort(key=lambda e: (1 if e["published_tiktok"] else 0))

    return entries, tasks


def _build_anna_schedule(db, today):
    """Build schedule for Ava (AnnaVideo).
    Published videos use actual pub dates; unpublished start from today at 2/day.
    """
    videos = db.query(AnnaVideo).order_by(AnnaVideo.id.asc()).all()

    published = [v for v in videos if v.published_tiktok]
    unpublished = [v for v in videos if not v.published_tiktok]
    published.sort(key=lambda v: v.published_tiktok)

    entries = []
    tasks = []

    # Published videos → actual dates
    date_slots = {}
    for v in published:
        tt_date = v.published_tiktok.date() if hasattr(v.published_tiktok, 'date') else v.published_tiktok
        slot_n = date_slots.get(tt_date, 0)
        slot = "morning" if slot_n % 2 == 0 else "evening"
        date_slots[tt_date] = slot_n + 1

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/anna",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "has_final": True,
            "slot": slot,
            "published_tiktok": True,
            "status": "Published",
            "status_color": "#16a34a",
        })
        if tt_date == today:
            tasks.append({
                "creator": "ava",
                "title": v.title[:60] if v.title else f"Video #{v.id}",
                "link": "/anna",
                "platform": "TikTok",
                "date": tt_date,
                "slot": slot,
                "script_id": None,
                "publish_url": f"/api/anna/{v.id}/toggle-publish",
                "published": True,
                "has_final": True,
                "status": "Published",
                "status_color": "#16a34a",
            })

    # Unpublished videos → fill from next slot after last published
    if date_slots:
        last_pub_date = max(date_slots.keys())
        slots_on_last = date_slots[last_pub_date]
    else:
        last_pub_date = SCHEDULE_STARTS.get("ava", today)
        slots_on_last = 0
    for i, v in enumerate(unpublished):
        adj_i = i + slots_on_last
        base_date = last_pub_date + timedelta(days=adj_i // 2)
        slot = "morning" if adj_i % 2 == 0 else "evening"
        tt_date = base_date
        is_ready = v.production_status in ("ready", "published")
        status = "Video Ready" if is_ready else "Draft"
        status_color = "#2563eb" if is_ready else "#d1d5db"

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/anna",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "has_final": is_ready,
            "slot": slot,
            "published_tiktok": False,
            "status": status,
            "status_color": status_color,
        })
        if tt_date == today:
            tasks.append({
                "creator": "ava",
                "title": v.title[:60] if v.title else f"Video #{v.id}",
                "link": "/anna",
                "platform": "TikTok",
                "date": tt_date,
                "slot": slot,
                "script_id": None,
                "publish_url": f"/api/anna/{v.id}/toggle-publish",
                "published": False,
                "has_final": is_ready,
                "status": status,
                "status_color": status_color,
            })

    # Published to bottom of the table
    entries.sort(key=lambda e: (1 if e["published_tiktok"] else 0))

    return entries, tasks


@router.get("/videos", response_class=HTMLResponse)
def videos_page(request: Request, db: Session = Depends(get_db)):
    today = datetime.now(EDT).date()

    schedule = {}
    todays_tasks = []

    for creator in CREATORS:
        if creator == "sophia":
            entries, tasks = _build_nari_schedule(db, today)
        elif creator == "ava":
            entries, tasks = _build_anna_schedule(db, today)
        else:
            entries, tasks = _build_script_schedule(db, creator, today)

        todays_tasks.extend(tasks)

        # Count photos
        photo_dir = os.path.join(PHOTOS_DIR, creator)
        photos = len([f for f in os.listdir(photo_dir) if not f.startswith(".")]) if os.path.isdir(photo_dir) else 0

        # Count subtitled / published
        subtitled = sum(1 for e in entries if e.get("status") == "Subtitled" or e.get("has_final"))
        published = sum(1 for e in entries if e["published_tiktok"])

        schedule[creator] = {
            "scripts": entries,
            "count": len(entries),
            "photos": photos,
            "subtitled": subtitled,
            "published": published,
        }

    # Build calendar dynamically from actual entry dates
    all_tt_dates = []
    for creator in CREATORS:
        for entry in schedule[creator]["scripts"]:
            all_tt_dates.append(entry["tiktok_date"])
    if all_tt_dates:
        cal_start = min(all_tt_dates)
        cal_end = max(max(all_tt_dates), today + timedelta(days=7))
        num_days = max((cal_end - cal_start).days + 1, 28)
    else:
        cal_start = today
        num_days = 28
    cal_days = [cal_start + timedelta(days=d) for d in range(num_days)]

    # For each creator, map date → list of entries for the calendar
    cal_data = {}
    for creator in CREATORS:
        day_map = {}
        for entry in schedule[creator]["scripts"]:
            d = entry["tiktok_date"]
            if d not in day_map:
                day_map[d] = []
            day_map[d].append(entry)
        cal_data[creator] = day_map

    # Grand totals
    totals = {
        "count": sum(schedule[c]["count"] for c in CREATORS),
        "photos": sum(schedule[c]["photos"] for c in CREATORS),
        "subtitled": sum(schedule[c]["subtitled"] for c in CREATORS),
        "published": sum(schedule[c]["published"] for c in CREATORS),
    }

    return templates.TemplateResponse(
        "videos.html",
        {
            "request": request,
            "active_page": "videos",
            "schedule": schedule,
            "creators": CREATORS,
            "todays_tasks": todays_tasks,
            "today": today,
            "cal_days": cal_days,
            "cal_data": cal_data,
            "totals": totals,
        }
    )
