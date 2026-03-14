"""Batch extract + rewrite all pending videos. Run inside container."""
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import SessionLocal
from models import Video, Script, Search
from services.pipeline import extract_script_for_video
from services.rewriter import rewrite_provocative

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

MAX_EXTRACT_WORKERS = 3


def batch_extract():
    db = SessionLocal()
    video_ids = [
        v.id for v in db.query(Video).filter(Video.status == "found").all()
    ]
    db.close()
    log.info(f"Extracting {len(video_ids)} videos with {MAX_EXTRACT_WORKERS} workers...")

    done = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=MAX_EXTRACT_WORKERS) as pool:
        futures = {pool.submit(extract_script_for_video, vid): vid for vid in video_ids}
        for future in as_completed(futures):
            vid = futures[future]
            try:
                future.result()
                done += 1
            except Exception as e:
                failed += 1
                log.error(f"Video {vid} failed: {e}")
            if (done + failed) % 10 == 0:
                log.info(f"Progress: {done + failed}/{len(video_ids)} (ok={done}, fail={failed})")

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


if __name__ == "__main__":
    log.info("=== BATCH PROCESSING START ===")
    batch_extract()
    batch_rewrite()
    log.info("=== ALL DONE ===")
