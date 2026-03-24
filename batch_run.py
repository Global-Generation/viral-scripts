"""Batch generate video prompts, metadata (and optionally rewrite scripts) for assigned scripts.

Usage:
    python batch_run.py              # only scripts missing prompts
    python batch_run.py --force      # regenerate ALL video prompts + metadata
    python batch_run.py --rewrite    # rewrite modified_text + regenerate video prompts + metadata
    python batch_run.py --daniel     # only Daniel's scripts
    python batch_run.py --boris      # only Boris's scripts (uses provocative Boris rewrite)
    python batch_run.py --thomas     # only Thomas's scripts
    python batch_run.py --zoe        # only Zoe's scripts
    python batch_run.py --natalie    # only Natalie's scripts
    python batch_run.py --luna       # only Luna's scripts
    python batch_run.py --rewrite --boris --force  # full regeneration for Boris
"""
import sys
import json
import logging
import anthropic
from database import SessionLocal
from models import Script
from services.prompter import generate_video_prompt
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

force = "--force" in sys.argv
rewrite = "--rewrite" in sys.argv

# Character filter — supports --daniel, --boris, --thomas, --zoe, --natalie, --luna
character_filter = None
for name in ["daniel", "boris", "thomas", "zoe", "natalie", "luna"]:
    if f"--{name}" in sys.argv:
        character_filter = name
        break

db = SessionLocal()
q = db.query(Script).filter(
    Script.assigned_to != "",
    Script.assigned_to.isnot(None),
)

if character_filter:
    q = q.filter(Script.assigned_to == character_filter)

if not force and not rewrite:
    q = q.filter((Script.video1_prompt == "") | (Script.video1_prompt.is_(None)))

scripts = q.all()
logger.info(f"Found {len(scripts)} scripts to process (force={force}, rewrite={rewrite}, character={character_filter or 'all'})")

# Step 1: Rewrite modified_text if --rewrite
if rewrite:
    from services.rewriter import rewrite_provocative, rewrite_provocative_boris
    rcount = 0
    rerrors = 0
    for s in scripts:
        if not s.original_text:
            continue
        try:
            if s.assigned_to == "boris":
                s.modified_text = rewrite_provocative_boris(s.original_text)
            else:
                s.modified_text = rewrite_provocative(s.original_text)
            db.commit()
            rcount += 1
            logger.info(f"Rewritten #{s.id} [{s.assigned_to}] ({rcount}/{len(scripts)})")
        except Exception as e:
            rerrors += 1
            logger.error(f"Rewrite failed #{s.id}: {e}")
    logger.info(f"REWRITE DONE: rewritten={rcount}, errors={rerrors}")

# Step 2: Generate video prompts
count = 0
errors = 0
for s in scripts:
    text = s.modified_text or s.original_text
    if not text:
        continue
    try:
        result = generate_video_prompt(text)
        s.video1_prompt = result["video1"]
        s.video2_prompt = result["video2"]
        s.video_prompt = result["video1"] + "\n\n" + result["video2"]
        db.commit()
        count += 1
        logger.info(f"Prompts #{s.id} ({count}/{len(scripts)})")
    except Exception as e:
        errors += 1
        logger.error(f"Prompts failed #{s.id}: {e}")

logger.info(f"PROMPTS DONE: generated={count}, errors={errors}")

# Step 3: Generate metadata (title, description, tags per platform)
meta_count = 0
meta_errors = 0
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

for s in scripts:
    text = s.modified_text or s.original_text
    if not text:
        continue
    try:
        prompt = f"""You are a social media expert. Given this video script, generate publication metadata for 3 platforms.

SCRIPT:
{text[:3000]}

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

        s.pub_title_tiktok = data.get("tiktok", {}).get("title", "")
        s.pub_desc_tiktok = data.get("tiktok", {}).get("description", "")
        s.pub_tags_tiktok = data.get("tiktok", {}).get("tags", "")
        s.pub_title_instagram = data.get("instagram", {}).get("title", "")
        s.pub_desc_instagram = data.get("instagram", {}).get("description", "")
        s.pub_tags_instagram = data.get("instagram", {}).get("tags", "")
        s.pub_title_youtube = data.get("youtube", {}).get("title", "")
        s.pub_desc_youtube = data.get("youtube", {}).get("description", "")
        s.pub_tags_youtube = data.get("youtube", {}).get("tags", "")
        db.commit()
        meta_count += 1
        logger.info(f"Metadata #{s.id} ({meta_count}/{len(scripts)})")
    except Exception as e:
        meta_errors += 1
        logger.error(f"Metadata failed #{s.id}: {e}")

db.close()
print(f"DONE: prompts={count}, metadata={meta_count}, errors(prompts={errors}, metadata={meta_errors})")
