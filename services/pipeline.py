import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Video, Script
from services.downloader import download_audio, cleanup_file
from services.transcriber import transcribe

logger = logging.getLogger(__name__)


def extract_script_for_video(video_id: int):
    db: Session = SessionLocal()
    try:
        video = db.query(Video).get(video_id)
        if not video:
            logger.error(f"Video {video_id} not found in pipeline")
            return

        video.status = "extracting"
        db.commit()

        # 1. Download audio
        audio_path = None
        try:
            audio_path = download_audio(video.tiktok_url, video.id)
        except Exception as e:
            logger.error(f"Download failed for video {video_id}: {e}")
            video.status = "failed"
            video.error_message = f"Download failed: {str(e)[:500]}"
            db.commit()
            return

        # 2. Transcribe
        try:
            text = transcribe(audio_path)
        except Exception as e:
            logger.error(f"Transcription failed for video {video_id}: {e}")
            video.status = "failed"
            video.error_message = f"Transcription failed: {str(e)[:500]}"
            db.commit()
            return
        finally:
            if audio_path:
                cleanup_file(audio_path)

        # 3. Save script
        existing = db.query(Script).filter(Script.video_id == video.id).first()
        if existing:
            existing.original_text = text
            existing.modified_text = ""
            existing.status = "extracted"
        else:
            db.add(Script(
                video_id=video.id,
                original_text=text,
                status="extracted",
            ))

        video.status = "extracted"
        db.commit()
        logger.info(f"Script extracted for video {video_id}, length={len(text)}")

    except Exception as e:
        logger.exception(f"Pipeline error for video {video_id}: {e}")
        try:
            video = db.query(Video).get(video_id)
            if video:
                video.status = "failed"
                video.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
