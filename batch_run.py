"""Batch generate video prompts for all assigned scripts.

Usage:
    python batch_run.py          # only scripts missing prompts
    python batch_run.py --force  # regenerate ALL assigned scripts
"""
import sys
import logging
from database import SessionLocal
from models import Script
from services.prompter import generate_video_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

force = "--force" in sys.argv

db = SessionLocal()
q = db.query(Script).filter(
    Script.assigned_to != "",
    Script.assigned_to.isnot(None),
)
if not force:
    q = q.filter((Script.video_prompt == "") | (Script.video_prompt.is_(None)))

scripts = q.all()
logger.info(f"Found {len(scripts)} scripts to process (force={force})")

count = 0
errors = 0
for s in scripts:
    text = s.modified_text or s.original_text
    if not text:
        continue
    try:
        prompt = generate_video_prompt(text)
        s.video_prompt = prompt
        db.commit()
        count += 1
        logger.info(f"Done #{s.id} ({count}/{len(scripts)})")
    except Exception as e:
        errors += 1
        logger.error(f"Failed #{s.id}: {e}")

db.close()
print(f"DONE: generated={count}, errors={errors}")
