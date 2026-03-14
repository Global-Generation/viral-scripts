import logging
import threading
import whisper
from config import WHISPER_MODEL

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()
TRANSCRIBE_TIMEOUT = 90  # seconds


def get_model():
    global _model
    with _model_lock:
        if _model is None:
            logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
            _model = whisper.load_model(WHISPER_MODEL)
            logger.info("Whisper model loaded")
    return _model


def transcribe(audio_path: str) -> str:
    model = get_model()
    result_box = [None]
    error_box = [None]

    def _run():
        try:
            result_box[0] = model.transcribe(
                audio_path, language=None, fp16=False, verbose=False,
            )
        except Exception as e:
            error_box[0] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=TRANSCRIBE_TIMEOUT)

    if t.is_alive():
        logger.error(f"Transcription timed out after {TRANSCRIBE_TIMEOUT}s: {audio_path}")
        raise RuntimeError(f"Transcription timed out after {TRANSCRIBE_TIMEOUT}s")
    if error_box[0]:
        raise error_box[0]
    if result_box[0] is None:
        raise RuntimeError("Transcription returned no result")

    return result_box[0].get("text", "").strip()
