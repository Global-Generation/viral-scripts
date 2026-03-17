"""Batch generate video prompts (and optionally rewrite scripts) for all assigned scripts.

Usage:
    python batch_run.py              # only scripts missing prompts
    python batch_run.py --force      # regenerate ALL video prompts
    python batch_run.py --rewrite    # rewrite modified_text + regenerate video prompts
"""
import sys
import logging
from database import SessionLocal
from models import Script
from services.prompter import generate_video_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

force = "--force" in sys.argv
rewrite = "--rewrite" in sys.argv

db = SessionLocal()
q = db.query(Script).filter(
    Script.assigned_to != "",
    Script.assigned_to.isnot(None),
)
if not force and not rewrite:
    q = q.filter((Script.video1_prompt == "") | (Script.video1_prompt.is_(None)))

scripts = q.all()
logger.info(f"Found {len(scripts)} scripts to process (force={force}, rewrite={rewrite})")

# Step 1: Rewrite modified_text if --rewrite
if rewrite:
    from services.rewriter import rewrite_provocative
    rcount = 0
    rerrors = 0
    for s in scripts:
        if not s.original_text:
            continue
        try:
            s.modified_text = rewrite_provocative(s.original_text)
            db.commit()
            rcount += 1
            logger.info(f"Rewritten #{s.id} ({rcount}/{len(scripts)})")
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
        logger.info(f"Done #{s.id} ({count}/{len(scripts)})")
    except Exception as e:
        errors += 1
        logger.error(f"Failed #{s.id}: {e}")

db.close()
print(f"DONE: generated={count}, errors={errors}")
