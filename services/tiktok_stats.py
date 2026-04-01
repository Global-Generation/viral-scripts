"""Fetch TikTok profile and video statistics."""
import json
import logging
import re
from typing import Optional

import httpx
import yt_dlp

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}


def fetch_profile_stats(tiktok_url: str) -> Optional[dict]:
    """Fetch profile-level stats: followers, hearts, videoCount."""
    try:
        resp = httpx.get(tiktok_url, headers=_HEADERS, follow_redirects=True, timeout=15)
        m = re.search(
            r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            resp.text,
            re.DOTALL,
        )
        if not m:
            return None
        data = json.loads(m.group(1))
        ui = (
            data.get("__DEFAULT_SCOPE__", {})
            .get("webapp.user-detail", {})
            .get("userInfo", {})
        )
        if not ui:
            return None
        stats = ui.get("stats", {})
        user = ui.get("user", {})
        return {
            "nickname": user.get("nickname", ""),
            "username": user.get("uniqueId", ""),
            "avatar": user.get("avatarMedium", ""),
            "followers": stats.get("followerCount", 0),
            "following": stats.get("followingCount", 0),
            "hearts": stats.get("heartCount", 0),
            "videos": stats.get("videoCount", 0),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch TikTok profile for {tiktok_url}: {e}")
        return None


def fetch_video_stats(tiktok_url: str, max_videos: int = 50) -> Optional[list[dict]]:
    """Fetch per-video stats using yt-dlp."""
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 20,
            "extract_flat": False,
            "playlistend": max_videos,
            "http_headers": _HEADERS,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tiktok_url, download=False)

        entries = list(info.get("entries", []))
        videos = []
        for e in entries:
            videos.append({
                "id": e.get("id", ""),
                "title": e.get("title", "")[:80],
                "url": e.get("webpage_url") or e.get("url", ""),
                "views": e.get("view_count", 0) or 0,
                "likes": e.get("like_count", 0) or 0,
                "comments": e.get("comment_count", 0) or 0,
                "shares": e.get("repost_count", 0) or 0,
                "saves": e.get("save_count", 0) or 0,
                "duration": e.get("duration", 0) or 0,
                "date": e.get("timestamp", 0),
            })
        return videos
    except Exception as e:
        logger.warning(f"Failed to fetch TikTok videos for {tiktok_url}: {e}")
        return None
