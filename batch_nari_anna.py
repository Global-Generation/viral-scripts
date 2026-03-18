"""Batch generate publication metadata for Nari and Anna videos.

Usage:
    python batch_nari_anna.py              # generate metadata for videos missing it
    python batch_nari_anna.py --force      # regenerate ALL metadata
    python batch_nari_anna.py --set-filmed # set all to 'filmed' status
"""
import json
import logging
import sys
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from database import SessionLocal
from models import NariVideo, AnnaVideo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

force = "--force" in sys.argv
set_filmed = "--set-filmed" in sys.argv

db = SessionLocal()

# Optionally set all to "filmed"
if set_filmed:
    for Model, name in [(NariVideo, "nari"), (AnnaVideo, "anna")]:
        updated = 0
        for v in db.query(Model).all():
            if v.production_status not in ("filmed", "published"):
                v.production_status = "filmed"
                updated += 1
        db.commit()
        logger.info(f"{name}: set {updated} videos to 'filmed'")

# Generate metadata
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
count = 0
errors = 0

for Model, name in [(NariVideo, "nari"), (AnnaVideo, "anna")]:
    videos = db.query(Model).order_by(Model.id).all()
    for v in videos:
        if not force and v.pub_title_tiktok:
            continue
        try:
            prompt = f"""You are a social media expert. Given this video title, generate publication metadata for 3 platforms.
The video is about personal finance / money advice, filmed by a young woman speaking to camera.

VIDEO TITLE:
{v.title}

Generate JSON with this exact structure (no markdown, just raw JSON):
{{
  "tiktok": {{
    "title": "short catchy title under 60 chars with hooks",
    "description": "2-3 sentences with emojis, call-to-action, under 150 chars",
    "tags": "#hashtag1 #hashtag2 #hashtag3 (10-15 relevant trending hashtags)"
  }},
  "instagram": {{
    "title": "catchy title under 60 chars",
    "description": "3-4 sentences with emojis, storytelling hook, call-to-action, under 300 chars",
    "tags": "#hashtag1 #hashtag2 (15-20 relevant hashtags)"
  }},
  "youtube": {{
    "title": "SEO-optimized title under 70 chars",
    "description": "5-7 sentences with SEO keywords, call-to-action, links placeholder, under 500 chars",
    "tags": "tag1, tag2, tag3 (10-15 comma-separated SEO tags)"
  }}
}}"""

            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)

            v.pub_title_tiktok = data.get("tiktok", {}).get("title", "")
            v.pub_desc_tiktok = data.get("tiktok", {}).get("description", "")
            v.pub_tags_tiktok = data.get("tiktok", {}).get("tags", "")
            v.pub_title_instagram = data.get("instagram", {}).get("title", "")
            v.pub_desc_instagram = data.get("instagram", {}).get("description", "")
            v.pub_tags_instagram = data.get("instagram", {}).get("tags", "")
            v.pub_title_youtube = data.get("youtube", {}).get("title", "")
            v.pub_desc_youtube = data.get("youtube", {}).get("description", "")
            v.pub_tags_youtube = data.get("youtube", {}).get("tags", "")
            db.commit()
            count += 1
            logger.info(f"{name} #{v.id} metadata done ({count})")
        except Exception as e:
            errors += 1
            logger.error(f"{name} #{v.id} failed: {e}")

db.close()
print(f"DONE: metadata={count}, errors={errors}")
