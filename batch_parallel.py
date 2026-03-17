"""Parallel batch extractor — splits videos across N worker processes."""
import logging
import sys
import multiprocessing
from database import SessionLocal
from models import Video

logging.basicConfig(level=logging.INFO, format="%(asctime)s [W%(process)d] %(message)s")
log = logging.getLogger(__name__)


def worker(video_ids, worker_id):
    """Process a chunk of video IDs sequentially."""
    from services.pipeline import extract_script_for_video
    log.info(f"Worker {worker_id} starting with {len(video_ids)} videos")
    done = 0
    failed = 0
    for i, vid in enumerate(video_ids):
        try:
            extract_script_for_video(vid)
            done += 1
        except Exception as e:
            failed += 1
            log.error(f"W{worker_id} video {vid} failed: {e}")
        if (i + 1) % 5 == 0:
            log.info(f"W{worker_id} progress: {i+1}/{len(video_ids)} (ok={done}, fail={failed})")
    log.info(f"W{worker_id} DONE: {done} ok, {failed} failed")


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    db = SessionLocal()
    # Reset stuck
    stuck = db.query(Video).filter(Video.status == "extracting").all()
    for v in stuck:
        v.status = "found"
    db.commit()

    video_ids = [v.id for v in db.query(Video).filter(Video.status == "found").order_by(Video.id).all()]
    db.close()

    if not video_ids:
        log.info("No videos to extract!")
        return

    log.info(f"Total: {len(video_ids)} videos, splitting across {n_workers} workers")

    # Split into chunks
    chunks = [[] for _ in range(n_workers)]
    for i, vid in enumerate(video_ids):
        chunks[i % n_workers].append(vid)

    processes = []
    for i, chunk in enumerate(chunks):
        p = multiprocessing.Process(target=worker, args=(chunk, i))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    log.info("=== ALL WORKERS DONE ===")


if __name__ == "__main__":
    main()
