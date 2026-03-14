import logging
import whisper
from config import WHISPER_MODEL

logger = logging.getLogger(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
        _model = whisper.load_model(WHISPER_MODEL)
        logger.info("Whisper model loaded")
    return _model


def transcribe(audio_path: str) -> str:
    model = get_model()
    result = model.transcribe(
        audio_path,
        language=None,
        fp16=False,
        verbose=False,
    )
    return result.get("text", "").strip()
