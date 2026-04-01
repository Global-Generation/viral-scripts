"""Daily TikTok stats scheduler — auto-refreshes profile stats for all creators."""
import json
import logging
from datetime import datetime, timezone, date

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _refresh_all_daily():
    """Fetch profile stats for all creators, update cache + append to log."""
    from database import SessionLocal
    from models import TiktokStats, TiktokStatsLog
    from routers.character import CHARACTERS
    from services.tiktok_stats import fetch_profile_stats

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    today = date.today()
    ok = 0
    fail = 0

    try:
        for name, info in CHARACTERS.items():
            tiktok_url = info.get("tiktok", "")
            if not tiktok_url:
                continue

            # Skip if already logged today
            existing = db.query(TiktokStatsLog).filter(
                TiktokStatsLog.creator == name,
                TiktokStatsLog.logged_at >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc),
            ).first()
            if existing:
                continue

            profile = fetch_profile_stats(tiktok_url)
            if not profile:
                fail += 1
                logger.warning(f"Scheduler: failed to fetch stats for {name}")
                continue

            # Update cache (TiktokStats)
            row = db.query(TiktokStats).filter(
                TiktokStats.creator == name, TiktokStats.stat_type == "profile"
            ).first()
            if row:
                row.data = json.dumps(profile)
                row.updated_at = now
            else:
                db.add(TiktokStats(creator=name, stat_type="profile", data=json.dumps(profile), updated_at=now))

            # Append to log (TiktokStatsLog)
            db.add(TiktokStatsLog(
                creator=name,
                followers=profile.get("followers", 0),
                hearts=profile.get("hearts", 0),
                videos=profile.get("videos", 0),
                following=profile.get("following", 0),
                logged_at=now,
            ))
            ok += 1

        db.commit()
        logger.info(f"Scheduler: TikTok stats refreshed — {ok} ok, {fail} failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Scheduler: TikTok stats refresh error: {e}")
    finally:
        db.close()


def _refresh_video_stats():
    """Fetch per-video stats (views, likes, etc.) for all creators via yt-dlp."""
    from database import SessionLocal
    from models import TiktokStats
    from routers.character import CHARACTERS
    from services.tiktok_stats import fetch_video_stats

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    ok = 0
    fail = 0

    try:
        for name, info in CHARACTERS.items():
            tiktok_url = info.get("tiktok", "")
            if not tiktok_url:
                continue

            videos = fetch_video_stats(tiktok_url)
            if videos is None:
                fail += 1
                logger.warning(f"Scheduler: failed to fetch video stats for {name}")
                continue

            row = db.query(TiktokStats).filter(
                TiktokStats.creator == name, TiktokStats.stat_type == "videos"
            ).first()
            if row:
                row.data = json.dumps(videos)
                row.updated_at = now
            else:
                db.add(TiktokStats(creator=name, stat_type="videos", data=json.dumps(videos), updated_at=now))
            ok += 1

        db.commit()
        logger.info(f"Scheduler: video stats refreshed — {ok} ok, {fail} failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Scheduler: video stats refresh error: {e}")
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    # Profile stats: daily at 06:00 UTC (02:00 EDT)
    _scheduler.add_job(_refresh_all_daily, "cron", hour=6, minute=0, id="tiktok_daily")
    _scheduler.add_job(_refresh_all_daily, "date", run_date=datetime.now(timezone.utc), id="tiktok_startup")
    # Video stats (views): every 3 hours
    _scheduler.add_job(_refresh_video_stats, "interval", hours=3, id="video_stats_3h")
    _scheduler.add_job(_refresh_video_stats, "date", run_date=datetime.now(timezone.utc), id="video_stats_startup")
    _scheduler.start()
    logger.info("TikTok stats scheduler started (profile: daily 06:00 UTC, video stats: every 3h)")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("TikTok stats scheduler stopped")
