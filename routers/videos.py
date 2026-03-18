import logging
from datetime import date, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Script, Video

router = APIRouter(tags=["videos"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

CREATORS = ["daniel", "boris", "thomas", "sophia", "ava"]
PUB_OFFSETS = {"tiktok": 0, "instagram": 7, "youtube": 14}

# Per-creator start dates
SCHEDULE_STARTS = {
    "daniel": date(2026, 3, 18),
    "boris": date(2026, 3, 18),
    "thomas": date(2026, 3, 18),
    "sophia": date(2026, 3, 16),
    "ava": date(2026, 3, 16),
}


@router.get("/videos", response_class=HTMLResponse)
def videos_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()

    # Build schedule: per-creator, only scripts with prompts ready
    schedule = {}
    todays_tasks = []

    for creator in CREATORS:
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

        # Assign dates: 1 script per day per creator
        script_dates = []
        start = SCHEDULE_STARTS.get(creator, date(2026, 3, 18))
        for i, script in enumerate(scripts):
            base_date = start + timedelta(days=i)
            tt_date = base_date + timedelta(days=PUB_OFFSETS["tiktok"])
            ig_date = base_date + timedelta(days=PUB_OFFSETS["instagram"])
            yt_date = base_date + timedelta(days=PUB_OFFSETS["youtube"])

            entry = {
                "script": script,
                "tiktok_date": tt_date,
                "instagram_date": ig_date,
                "youtube_date": yt_date,
                "has_pub_meta": bool(script.pub_title_tiktok),
            }
            script_dates.append(entry)

            # Check if any platform is due today
            if tt_date == today:
                todays_tasks.append({
                    "creator": creator,
                    "script": script,
                    "platform": "TikTok",
                    "date": tt_date,
                })
            if ig_date == today:
                todays_tasks.append({
                    "creator": creator,
                    "script": script,
                    "platform": "Instagram",
                    "date": ig_date,
                })
            if yt_date == today:
                todays_tasks.append({
                    "creator": creator,
                    "script": script,
                    "platform": "YouTube",
                    "date": yt_date,
                })

        schedule[creator] = {
            "scripts": script_dates,
            "count": len(scripts),
        }

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
        }
    )
