import logging
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Script, Video, NariVideo, AnnaVideo

# US Eastern = UTC-4 (EDT) / UTC-5 (EST). Using EDT for now.
EDT = timezone(timedelta(hours=-4))

router = APIRouter(tags=["videos"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

CREATORS = ["daniel", "boris", "thomas", "zoe", "natalie", "luna", "sophia", "ava"]
PUB_OFFSETS = {"tiktok": 0, "instagram": 7, "youtube": 14}

# Per-creator start dates
SCHEDULE_STARTS = {
    "daniel":  date(2026, 3, 24),
    "boris":   date(2026, 3, 24),
    "thomas":  date(2026, 3, 24),
    "zoe":     date(2026, 3, 24),
    "natalie": date(2026, 3, 24),
    "luna":    date(2026, 3, 24),
    "sophia":  date(2026, 3, 16),
    "ava":     date(2026, 3, 16),
}


def _script_status(script):
    """Return (status_label, status_color) for a script."""
    if script.published_tiktok or script.published_instagram or script.published_youtube:
        return "Published", "#16a34a"
    if script.final_subtitled_path:
        return "Subtitled", "#0891b2"
    if script.subtitle_status == "processing":
        return "Adding Subs", "#8b5cf6"
    if script.final_video_path:
        return "Video Ready", "#2563eb"
    if script.raw_video1_path or script.raw_video2_path:
        return "Filmed", "#ca8a04"
    if script.modified_text:
        return "Script Only", "#9ca3af"
    return "Draft", "#d1d5db"


def _build_script_schedule(db, creator, today):
    """Build schedule for script-based creators (daniel, boris, thomas)."""
    scripts = (
        db.query(Script)
        .options(joinedload(Script.video))
        .filter(
            Script.assigned_to == creator,
            Script.video1_prompt != "",
            Script.video1_prompt.isnot(None),
            Script.video2_prompt != "",
            Script.video2_prompt.isnot(None),
        )
        .order_by(Script.id.asc())
        .all()
    )

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
        tt_date = base_date + timedelta(days=PUB_OFFSETS["tiktok"])
        ig_date = base_date + timedelta(days=PUB_OFFSETS["instagram"])
        yt_date = base_date + timedelta(days=PUB_OFFSETS["youtube"])

        s_label, s_color = _script_status(script)
        title = script.pub_title_tiktok or (script.video.title if script.video else None) or f"Script #{script.id}"
        entries.append({
            "title": title[:55],
            "link": f"/scripts/{script.id}",
            "script_id": script.id,
            "has_raw_video": bool(script.raw_video1_path or script.final_video_path),
            "tiktok_date": tt_date,
            "instagram_date": ig_date,
            "youtube_date": yt_date,
            "has_final": bool(script.final_video_path or script.final_subtitled_path),
            "slot": slot,
            "published_tiktok": bool(script.published_tiktok),
            "published_instagram": bool(script.published_instagram),
            "published_youtube": bool(script.published_youtube),
            "status": s_label,
            "status_color": s_color,
        })

        link = f"/scripts/{script.id}"
        for platform, d in [("TikTok", tt_date), ("Instagram", ig_date), ("YouTube", yt_date)]:
            if d == today:
                plat_published = bool(getattr(script, f"published_{platform.lower()}"))
                if plat_published:
                    task_status, task_color = "Published", "#16a34a"
                elif s_label == "Published":
                    # TikTok published but this platform not yet
                    task_status, task_color = "Ready to Post", "#f59e0b"
                else:
                    task_status, task_color = s_label, s_color
                tasks.append({
                    "creator": creator,
                    "title": title[:60],
                    "link": link,
                    "platform": platform,
                    "date": d,
                    "slot": slot,
                    "script_id": script.id,
                    "published": plat_published,
                    "status": task_status,
                    "status_color": task_color,
                })

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
        ig_date = tt_date + timedelta(days=PUB_OFFSETS["instagram"])
        yt_date = tt_date + timedelta(days=PUB_OFFSETS["youtube"])

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/nari",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "instagram_date": ig_date,
            "youtube_date": yt_date,
            "has_final": True,
            "slot": slot,
            "published_tiktok": True,
            "published_instagram": bool(v.published_instagram),
            "published_youtube": bool(v.published_youtube),
            "status": "Published",
            "status_color": "#16a34a",
        })
        for platform, d in [("Instagram", ig_date), ("YouTube", yt_date)]:
            if d == today:
                plat_published = bool(getattr(v, f"published_{platform.lower()}"))
                tasks.append({
                    "creator": "sophia",
                    "title": v.title[:60] if v.title else f"Video #{v.id}",
                    "link": "/nari",
                    "platform": platform,
                    "date": d,
                    "slot": slot,
                    "script_id": None,
                    "published": plat_published,
                    "has_final": True,
                    "status": "Published" if plat_published else "Ready to Post",
                    "status_color": "#16a34a" if plat_published else "#f59e0b",
                })

    # Unpublished videos → from today at 2/day
    for i, v in enumerate(unpublished):
        base_date = today + timedelta(days=i // 2)
        slot = "morning" if i % 2 == 0 else "evening"
        tt_date = base_date
        ig_date = base_date + timedelta(days=PUB_OFFSETS["instagram"])
        yt_date = base_date + timedelta(days=PUB_OFFSETS["youtube"])
        is_ready = v.production_status in ("ready", "published")
        status = "Video Ready" if is_ready else "Draft"
        status_color = "#2563eb" if is_ready else "#d1d5db"

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/nari",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "instagram_date": ig_date,
            "youtube_date": yt_date,
            "has_final": is_ready,
            "slot": slot,
            "published_tiktok": False,
            "published_instagram": False,
            "published_youtube": False,
            "status": status,
            "status_color": status_color,
        })
        for platform, d in [("Instagram", ig_date), ("YouTube", yt_date)]:
            if d == today:
                tasks.append({
                    "creator": "sophia",
                    "title": v.title[:60] if v.title else f"Video #{v.id}",
                    "link": "/nari",
                    "platform": platform,
                    "date": d,
                    "slot": slot,
                    "script_id": None,
                    "published": False,
                    "has_final": is_ready,
                    "status": status,
                    "status_color": status_color,
                })

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
        ig_date = tt_date + timedelta(days=PUB_OFFSETS["instagram"])
        yt_date = tt_date + timedelta(days=PUB_OFFSETS["youtube"])

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/anna",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "instagram_date": ig_date,
            "youtube_date": yt_date,
            "has_final": True,
            "slot": slot,
            "published_tiktok": True,
            "published_instagram": bool(v.published_instagram),
            "published_youtube": bool(v.published_youtube),
            "status": "Published",
            "status_color": "#16a34a",
        })
        for platform, d in [("Instagram", ig_date), ("YouTube", yt_date)]:
            if d == today:
                plat_published = bool(getattr(v, f"published_{platform.lower()}"))
                tasks.append({
                    "creator": "ava",
                    "title": v.title[:60] if v.title else f"Video #{v.id}",
                    "link": "/anna",
                    "platform": platform,
                    "date": d,
                    "slot": slot,
                    "script_id": None,
                    "published": plat_published,
                    "has_final": True,
                    "status": "Published" if plat_published else "Ready to Post",
                    "status_color": "#16a34a" if plat_published else "#f59e0b",
                })

    # Unpublished videos → from today at 2/day
    for i, v in enumerate(unpublished):
        base_date = today + timedelta(days=i // 2)
        slot = "morning" if i % 2 == 0 else "evening"
        tt_date = base_date
        ig_date = base_date + timedelta(days=PUB_OFFSETS["instagram"])
        yt_date = base_date + timedelta(days=PUB_OFFSETS["youtube"])
        is_ready = v.production_status in ("ready", "published")
        status = "Video Ready" if is_ready else "Draft"
        status_color = "#2563eb" if is_ready else "#d1d5db"

        entries.append({
            "title": v.title[:55] if v.title else f"Video #{v.id}",
            "link": "/anna",
            "script_id": None,
            "has_raw_video": False,
            "tiktok_date": tt_date,
            "instagram_date": ig_date,
            "youtube_date": yt_date,
            "has_final": is_ready,
            "slot": slot,
            "published_tiktok": False,
            "published_instagram": False,
            "published_youtube": False,
            "status": status,
            "status_color": status_color,
        })
        for platform, d in [("Instagram", ig_date), ("YouTube", yt_date)]:
            if d == today:
                tasks.append({
                    "creator": "ava",
                    "title": v.title[:60] if v.title else f"Video #{v.id}",
                    "link": "/anna",
                    "platform": platform,
                    "date": d,
                    "slot": slot,
                    "script_id": None,
                    "published": False,
                    "has_final": is_ready,
                    "status": status,
                    "status_color": status_color,
                })

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
        schedule[creator] = {
            "scripts": entries,
            "count": len(entries),
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

    return templates.TemplateResponse(
        "videos.html",
        {
            "request": request,
            "active_page": "videos",
            "schedule": schedule,
            "creators": CREATORS,
            "pub_offsets": PUB_OFFSETS,
            "todays_tasks": todays_tasks,
            "today": today,
            "cal_days": cal_days,
            "cal_data": cal_data,
        }
    )
