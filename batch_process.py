"""Batch extract + rewrite all pending videos. Run inside container."""
import logging
from database import SessionLocal
from models import Video, Script
from services.pipeline import extract_script_for_video
from services.rewriter import rewrite_provocative
from services.classifier import classify_script
from services.scorer import score_viral_potential

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def batch_extract():
    db = SessionLocal()
    # Reset any stuck extracting videos
    stuck = db.query(Video).filter(Video.status == "extracting").all()
    for v in stuck:
        v.status = "found"
    db.commit()

    video_ids = [v.id for v in db.query(Video).filter(Video.status == "found").all()]
    db.close()
    log.info(f"Extracting {len(video_ids)} videos sequentially...")

    done = 0
    failed = 0
    for i, vid in enumerate(video_ids):
        try:
            extract_script_for_video(vid)
            done += 1
        except Exception as e:
            failed += 1
            log.error(f"Video {vid} failed: {e}")
        log.info(f"Progress: {i+1}/{len(video_ids)} (ok={done}, fail={failed})")

    log.info(f"Extraction done: {done} ok, {failed} failed out of {len(video_ids)}")
    return done


def batch_rewrite():
    db = SessionLocal()
    scripts = db.query(Script).filter(
        Script.original_text != "",
        Script.original_text.isnot(None),
        (Script.modified_text == "") | (Script.modified_text.is_(None)),
    ).all()
    log.info(f"Rewriting {len(scripts)} scripts...")

    done = 0
    errors = 0
    for script in scripts:
        try:
            rewritten = rewrite_provocative(script.original_text)
            script.modified_text = rewritten
            script.status = "modified"
            db.commit()
            done += 1
            log.info(f"Rewritten #{script.id} ({done}/{len(scripts)})")
        except Exception as e:
            errors += 1
            log.error(f"Rewrite failed #{script.id}: {e}")

    db.close()
    log.info(f"Rewrite done: {done} ok, {errors} errors")
    return done


def batch_classify():
    db = SessionLocal()
    scripts = db.query(Script).filter(
        Script.original_text != "",
        Script.original_text.isnot(None),
        (Script.character_type == "") | (Script.character_type.is_(None)),
    ).all()
    log.info(f"Classifying {len(scripts)} scripts...")

    done = 0
    errors = 0
    for script in scripts:
        try:
            char_type = classify_script(script.original_text)
            script.character_type = char_type
            db.commit()
            done += 1
            log.info(f"Classified #{script.id} -> {char_type} ({done}/{len(scripts)})")
        except Exception as e:
            errors += 1
            log.error(f"Classify failed #{script.id}: {e}")

    db.close()
    log.info(f"Classification done: {done} ok, {errors} errors")
    return done


def batch_score():
    db = SessionLocal()
    scripts = db.query(Script).filter(
        Script.original_text != "",
        Script.original_text.isnot(None),
        Script.viral_score == 0,
    ).all()
    log.info(f"Scoring {len(scripts)} scripts...")

    done = 0
    errors = 0
    for script in scripts:
        try:
            score = score_viral_potential(script.original_text)
            script.viral_score = score
            db.commit()
            done += 1
            log.info(f"Scored #{script.id} -> {score} ({done}/{len(scripts)})")
        except Exception as e:
            errors += 1
            log.error(f"Score failed #{script.id}: {e}")

    db.close()
    log.info(f"Scoring done: {done} ok, {errors} errors")
    return done


def batch_rewrite_force():
    """Re-rewrite ALL assigned scripts (force overwrite existing modified_text)."""
    db = SessionLocal()
    scripts = db.query(Script).filter(
        Script.original_text != "",
        Script.original_text.isnot(None),
        Script.assigned_to.isnot(None),
        Script.assigned_to != "",
    ).all()
    log.info(f"Force-rewriting {len(scripts)} assigned scripts...")

    done = 0
    errors = 0
    for script in scripts:
        try:
            rewritten = rewrite_provocative(script.original_text)
            script.modified_text = rewritten
            script.status = "modified"
            db.commit()
            done += 1
            log.info(f"Rewritten #{script.id} ({done}/{len(scripts)})")
        except Exception as e:
            errors += 1
            log.error(f"Rewrite failed #{script.id}: {e}")

    db.close()
    log.info(f"Force rewrite done: {done} ok, {errors} errors")
    return done


if __name__ == "__main__":
    import sys
    log.info("=== BATCH PROCESSING START ===")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "classify":
        batch_classify()
    elif cmd == "score":
        batch_score()
    elif cmd == "rewrite-force":
        batch_rewrite_force()
    else:
        batch_extract()
        batch_rewrite()
        batch_classify()
        batch_score()
    log.info("=== ALL DONE ===")
