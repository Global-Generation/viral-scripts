import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Script, Video, NariVideo, AnnaVideo, TiktokStats, TiktokStatsLog
from routers.character import CHARACTERS

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "photos")

# US Eastern = UTC-4 (EDT) / UTC-5 (EST). Using EDT for now.
EDT = timezone(timedelta(hours=-4))

router = APIRouter(tags=["videos"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

CREATORS = ["sophia", "ava", "daniel", "boris", "thomas", "zoe", "natalie", "luna"]

# Per-creator start dates
SCHEDULE_STARTS = {
    "daniel":  date(2026, 4, 1),
    "boris":   date(2026, 4, 1),
    "thomas":  date(2026, 4, 1),
    "zoe":     date(2026, 4, 1),
    "natalie": date(2026, 4, 1),
    "luna":    date(2026, 4, 1),
    "sophia":  date(2026, 4, 1),
    "ava":     date(2026, 4, 1),
}


def _script_status(script):
    """Return (status_label, status_color) for a script.
    4 statuses: Draft → Script Ready → Video Ready → Published.
    Published = only TikTok (YouTube date = scheduling, not publication).
    """
    if script.published_tiktok:
        return "Published", "#16a34a"
    if script.final_subtitled_path:
        return "Video Ready", "#2563eb"
    if script.modified_text:
        return "Script Ready", "#9ca3af"
    return "Draft", "#d1d5db"


def _build_script_schedule(db, creator, today):
    """Build schedule for script-based creators (daniel, boris, thomas, etc.).
    Published scripts use actual pub dates; unpublished start from today at 2/day.
    """
    scripts = (
        db.query(Script)
        .options(joinedload(Script.video))
        .filter(Script.assigned_to == creator)
        .order_by(Script.id.asc())
        .all()
    )

    published = [s for s in scripts if s.published_tiktok]
    unpublished = [s for s in scripts if not s.published_tiktok]
    published.sort(key=lambda s: s.published_tiktok)

    entries = []
    tasks = []

    # --- Published scripts: use actual published_tiktok dates ---
    date_slots = {}
    for script in published:
        tt_date = script.published_tiktok.date() if hasattr(script.published_tiktok, 'date') else script.published_tiktok
        slot_n = date_slots.get(tt_date, 0)
        slot = "morning" if slot_n % 2 == 0 else "evening"
        date_slots[tt_date] = slot_n + 1

        s_label, s_color = _script_status(script)
        title = script.pub_title_tiktok or (script.video.title if script.video else None) or f"Script #{script.id}"
        entries.append({
            "title": title[:55],
            "link": f"/scripts/{script.id}",
            "script_id": script.id,
            "has_raw_video": bool(script.raw_video1_path or script.final_video_path),
            "tiktok_date": tt_date,
            "has_final": bool(script.final_subtitled_path),
            "slot": slot,
            "published_tiktok": True,
            "published_youtube": script.published_youtube,
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
                "published": True,
                "status": s_label,
                "status_color": s_color,
            })

    # --- Unpublished scripts: sequential schedule from today ---
    def _readiness(s):
        if s.final_subtitled_path:
            return 0
        if s.modified_text:
            return 1
        return 2
    unpublished.sort(key=lambda s: (_readiness(s), s.id))

    if date_slots:
        last_pub_date = max(date_slots.keys())
        slots_on_last = date_slots[last_pub_date]
    else:
        last_pub_date = SCHEDULE_STARTS[creator]
        slots_on_last = 0
    effective_start = max(last_pub_date, today, SCHEDULE_STARTS[creator])
    if effective_start > last_pub_date:
        slots_on_last = 0

    for i, script in enumerate(unpublished):
        adj_i = i + slots_on_last
        base_date = effective_start + timedelta(days=adj_i // 2)
        slot = "morning" if adj_i % 2 == 0 else "evening"
        tt_date = base_date

        s_label, s_color = _script_status(script)
        title = script.pub_title_tiktok or (script.video.title if script.video else None) or f"Script #{script.id}"
        entries.append({
            "title": title[:55],
            "link": f"/scripts/{script.id}",
            "script_id": script.id,
            "has_raw_video": bool(script.raw_video1_path or script.final_video_path),
            "tiktok_date": tt_date,
            "has_final": bool(script.final_subtitled_path),
            "slot": slot,
            "published_tiktok": False,
            "published_youtube": script.published_youtube,
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
                "published": False,
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
            "published_youtube": None,
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

    # Unpublished videos → fill from next slot after last published (never in the past)
    if date_slots:
        last_pub_date = max(date_slots.keys())
        slots_on_last = date_slots[last_pub_date]
    else:
        last_pub_date = SCHEDULE_STARTS.get("sophia", today)
        slots_on_last = 0
    # Never schedule unpublished in the past, and respect SCHEDULE_STARTS
    effective_start = max(last_pub_date, today, SCHEDULE_STARTS.get("sophia", today))
    if effective_start > last_pub_date:
        slots_on_last = 0
    for i, v in enumerate(unpublished):
        adj_i = i + slots_on_last
        base_date = effective_start + timedelta(days=adj_i // 2)
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
            "published_youtube": None,
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
            "published_youtube": None,
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

    # Unpublished videos → fill from next slot after last published (never in the past)
    if date_slots:
        last_pub_date = max(date_slots.keys())
        slots_on_last = date_slots[last_pub_date]
    else:
        last_pub_date = SCHEDULE_STARTS.get("ava", today)
        slots_on_last = 0
    # Never schedule unpublished in the past, and respect SCHEDULE_STARTS
    effective_start = max(last_pub_date, today, SCHEDULE_STARTS.get("ava", today))
    if effective_start > last_pub_date:
        slots_on_last = 0
    for i, v in enumerate(unpublished):
        adj_i = i + slots_on_last
        base_date = effective_start + timedelta(days=adj_i // 2)
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
            "published_youtube": None,
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

        # Count exported (Video Ready) / published
        exported = sum(1 for e in entries if e.get("has_final"))
        published = sum(1 for e in entries if e["published_tiktok"])

        # YouTube: count scheduled (has published_youtube date) and ready for scheduling
        yt_scheduled = sum(1 for e in entries if e.get("published_youtube"))
        yt_ready = sum(1 for e in entries if e.get("has_final") and not e.get("published_youtube"))

        schedule[creator] = {
            "scripts": entries,
            "count": len(entries),
            "photos": photos,
            "exported": exported,
            "published": published,
            "yt_scheduled": yt_scheduled,
            "yt_ready": yt_ready,
        }

    # Sort today's tasks: most ready first
    _status_priority = {"Published": 0, "Video Ready": 1, "Script Ready": 2, "Draft": 3}
    todays_tasks.sort(key=lambda t: _status_priority.get(t["status"], 9))

    # YouTube dates: use published_youtube from DB (manual scheduling)
    for creator in CREATORS:
        for entry in schedule[creator]["scripts"]:
            yt_raw = entry["published_youtube"]  # datetime or None
            if yt_raw and hasattr(yt_raw, 'date'):
                entry["yt_date"] = yt_raw.date()
            elif yt_raw:
                entry["yt_date"] = yt_raw
            else:
                entry["yt_date"] = None

    # Build TikTok calendar dynamically from actual entry dates
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

    # For each creator, map date → list of entries for TikTok calendar
    cal_data = {}
    for creator in CREATORS:
        day_map = {}
        for entry in schedule[creator]["scripts"]:
            d = entry["tiktok_date"]
            if d not in day_map:
                day_map[d] = []
            day_map[d].append(entry)
        cal_data[creator] = day_map

    # Build YouTube calendar (from manual published_youtube dates)
    all_yt_dates = [e["yt_date"] for c in CREATORS for e in schedule[c]["scripts"] if e["yt_date"]]
    if all_yt_dates:
        yt_cal_start = min(all_yt_dates)
        yt_cal_end = max(max(all_yt_dates), today + timedelta(days=14))
        yt_num_days = max((yt_cal_end - yt_cal_start).days + 1, 28)
    else:
        yt_cal_start = today
        yt_num_days = 28
    yt_cal_days = [yt_cal_start + timedelta(days=d) for d in range(yt_num_days)]

    yt_cal_data = {}
    for creator in CREATORS:
        day_map = {}
        for entry in schedule[creator]["scripts"]:
            d = entry["yt_date"]
            if d is None:
                continue
            day_map.setdefault(d, []).append(entry)
        yt_cal_data[creator] = day_map

    # Grand totals
    exported_list = []
    published_list = []
    for c in CREATORS:
        for e in schedule[c]["scripts"]:
            item = {"creator": c, "title": e["title"], "link": e["link"], "script_id": e["script_id"], "tiktok_date": e["tiktok_date"].strftime("%b %d")}
            if e.get("has_final"):
                exported_list.append(item)
            if e.get("published_tiktok"):
                published_list.append(item)

    totals = {
        "count": sum(schedule[c]["count"] for c in CREATORS),
        "photos": sum(schedule[c]["photos"] for c in CREATORS),
        "exported": sum(schedule[c]["exported"] for c in CREATORS),
        "published": sum(schedule[c]["published"] for c in CREATORS),
        "yt_scheduled": sum(schedule[c]["yt_scheduled"] for c in CREATORS),
        "yt_ready": sum(schedule[c]["yt_ready"] for c in CREATORS),
        "exported_list": exported_list,
        "published_list": published_list,
    }

    # TikTok profile stats (cached)
    from zoneinfo import ZoneInfo
    ny_tz = ZoneInfo("America/New_York")
    tt_stats = {}
    tt_totals = {"followers": 0, "hearts": 0, "videos": 0, "views": 0}
    profile_rows = (
        db.query(TiktokStats)
        .filter(TiktokStats.stat_type == "profile")
        .order_by(TiktokStats.updated_at.desc())
        .all()
    )
    for row in profile_rows:
        if row.creator in tt_stats:
            continue  # skip older duplicates
        data = json.loads(row.data) if row.data else {}
        if row.updated_at:
            ut = row.updated_at.replace(tzinfo=timezone.utc) if row.updated_at.tzinfo is None else row.updated_at
            data["updated_at"] = ut.astimezone(ny_tz).strftime("%Y-%m-%d %I:%M %p")
        else:
            data["updated_at"] = None
        tt_stats[row.creator] = data
        tt_totals["followers"] += data.get("followers", 0)
        tt_totals["hearts"] += data.get("hearts", 0)
        tt_totals["videos"] += data.get("videos", 0)

    # TikTok per-video stats — sum views per creator
    video_rows = db.query(TiktokStats).filter(TiktokStats.stat_type == "videos").all()
    for row in video_rows:
        vids = json.loads(row.data) if row.data else []
        creator_views = sum(v.get("views", 0) for v in vids) if isinstance(vids, list) else 0
        if row.creator in tt_stats:
            tt_stats[row.creator]["views"] = creator_views
        else:
            tt_stats[row.creator] = {"views": creator_views}
        tt_totals["views"] += creator_views

    # Sort creators by views descending for the stats table
    creators_sorted = sorted(CREATORS, key=lambda c: tt_stats.get(c, {}).get("views", 0), reverse=True)

    # --- Deltas: since last refresh + since yesterday ---
    now_utc = datetime.now(timezone.utc)
    target_24h = now_utc - timedelta(hours=24)
    tt_totals["d_refresh"] = {"followers": 0, "hearts": 0, "videos": 0}
    tt_totals["d_day"] = {"followers": 0, "hearts": 0, "videos": 0}

    for c in CREATORS:
        if c not in tt_stats:
            continue
        logs = (
            db.query(TiktokStatsLog)
            .filter(TiktokStatsLog.creator == c)
            .order_by(TiktokStatsLog.logged_at.desc())
            .limit(50)
            .all()
        )
        if not logs:
            continue

        # Current values from live cache (not from log — log may lag behind)
        cur_f = tt_stats[c].get("followers", 0)
        cur_h = tt_stats[c].get("hearts", 0)
        cur_v = tt_stats[c].get("videos", 0)

        # Delta since last refresh (compare to most recent log entry)
        prev = logs[0]
        dr = {
            "followers": cur_f - prev.followers,
            "hearts": cur_h - prev.hearts,
            "videos": cur_v - prev.videos,
        }
        tt_stats[c]["d_refresh"] = dr
        for k in dr:
            tt_totals["d_refresh"][k] += dr[k]

        # Delta since ~24h ago
        past = None
        for log in logs:
            log_at = log.logged_at.replace(tzinfo=timezone.utc) if log.logged_at.tzinfo is None else log.logged_at
            if log_at <= target_24h:
                past = log
                break
        if past:
            dd = {
                "followers": cur_f - past.followers,
                "hearts": cur_h - past.hearts,
                "videos": cur_v - past.videos,
            }
            tt_stats[c]["d_day"] = dd
            for k in dd:
                tt_totals["d_day"][k] += dd[k]

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
            "yt_cal_days": yt_cal_days,
            "yt_cal_data": yt_cal_data,
            "totals": totals,
            "tiktok_links": {name: info.get("tiktok", "") for name, info in CHARACTERS.items()},
            "tt_stats": tt_stats,
            "tt_totals": tt_totals,
            "creators_sorted": creators_sorted,
        }
    )
