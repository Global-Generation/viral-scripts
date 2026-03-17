import os
import math
import logging
import subprocess
import urllib.request
import numpy as np
import stable_whisper
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip

from database import SessionLocal
from models import VideoGeneration
from services.subtitle_extractor import extract_dialogue

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "./downloads")

_whisper_model = None
_font_cache = {}


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        model_name = os.getenv("WHISPER_MODEL", "base")
        logger.info(f"Loading stable-ts Whisper model: {model_name}")
        _whisper_model = stable_whisper.load_model(model_name)
    return _whisper_model


def _get_font(size: int):
    """Get Futura Condensed ExtraBold, falling back gracefully."""
    size = max(8, int(size))
    if size not in _font_cache:
        # Futura.ttc index 4 = Condensed ExtraBold
        ttc_fonts = [
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),         # macOS Futura Condensed ExtraBold
        ]
        for p, idx in ttc_fonts:
            if os.path.exists(p):
                try:
                    _font_cache[size] = ImageFont.truetype(p, size, index=idx)
                    return _font_cache[size]
                except Exception:
                    continue
        paths = [
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",         # macOS fallback
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # Linux
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",        # Linux
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    _font_cache[size] = ImageFont.truetype(p, size)
                    return _font_cache[size]
                except Exception:
                    continue
        _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def _anim_pop(t, word_start, word_end):
    """Pop: smooth scale 1.0 → 1.25 → 1.0."""
    elapsed = t - word_start
    dur = min(0.2, (word_end - word_start) * 0.5)
    if elapsed < 0:
        return {"scale": 1.0, "alpha": 1.0}
    if elapsed < dur:
        p = elapsed / dur
        return {"scale": 1.0 + 0.25 * math.sin(p * math.pi), "alpha": 1.0}
    return {"scale": 1.0, "alpha": 1.0}


def _find_font_size(chunks, video_w, max_width_ratio=0.88):
    """Find largest font size where all chunks fit within max_width_ratio of video width."""
    max_w = int(video_w * max_width_ratio)
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)

    for size in range(60, 20, -2):
        font = _get_font(size)
        font_big = _get_font(int(size * 1.15 * 1.25))
        sp = draw.textbbox((0, 0), " ", font=font)[2]

        fits = True
        for chunk in chunks:
            tw = 0
            for i, w in enumerate(chunk):
                bb = draw.textbbox((0, 0), w["word"].upper(), font=font_big)
                tw += bb[2] - bb[0]
                if i < len(chunk) - 1:
                    tw += sp
            if tw > max_w:
                fits = False
                break
        if fits:
            return size
    return 24


def _render_chunk(words, active_idx, video_w, video_h, anim, base_size):
    """Render chunk: WHITE BOLD UPPERCASE, YELLOW active word with pop."""
    scale = anim["scale"]
    alpha_m = anim["alpha"]

    font = _get_font(base_size)
    font_a = _get_font(int(base_size * 1.15 * scale))

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    sp = draw.textbbox((0, 0), " ", font=font)[2]

    ms = []
    tw = 0
    mh = 0
    for i, w in enumerate(words):
        f = font_a if i == active_idx else font
        txt = w["word"].upper()
        bb = draw.textbbox((0, 0), txt, font=f)
        ww, hh = bb[2] - bb[0], bb[3] - bb[1]
        ms.append({"w": ww, "h": hh, "xo": -bb[0], "yo": -bb[1], "f": f})
        tw += ww
        mh = max(mh, hh)
        if i < len(words) - 1:
            tw += sp

    pad = 20
    img = Image.new("RGBA", (tw + pad * 2, mh + pad * 2 + 30), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    ol = max(2, base_size // 12)
    x = pad

    for i, w in enumerate(words):
        m = ms[i]
        txt = w["word"].upper()
        act = (i == active_idx)
        yb = pad + 15 + (mh - m["h"]) // 2
        yd = yb + m["yo"]
        xd = x + m["xo"]

        if act:
            a = max(0, min(255, int(255 * alpha_m)))
            for dx in range(-ol, ol + 1):
                for dy in range(-ol, ol + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((xd + dx, yd + dy), txt, font=m["f"], fill=(0, 0, 0, a))
            draw.text((xd, yd), txt, font=m["f"], fill=(255, 255, 0, a))
        else:
            for dx in range(-ol, ol + 1):
                for dy in range(-ol, ol + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((xd + dx, yd + dy), txt, font=m["f"], fill=(0, 0, 0, 200))
            draw.text((xd, yd), txt, font=m["f"], fill=(255, 255, 255, 255))
        x += m["w"] + sp

    return np.array(img)


def _align_words(known_words: list[str], whisper_words: list[dict]) -> list[dict]:
    if not known_words:
        return []

    if not whisper_words:
        duration = 5.0
        per_word = duration / len(known_words)
        return [
            {"word": w, "start": i * per_word, "end": (i + 1) * per_word}
            for i, w in enumerate(known_words)
        ]

    total_start = whisper_words[0]["start"]
    total_end = whisper_words[-1]["end"]

    if len(known_words) == len(whisper_words):
        return [
            {"word": known_words[i], "start": whisper_words[i]["start"], "end": whisper_words[i]["end"]}
            for i in range(len(known_words))
        ]

    duration = total_end - total_start
    if duration <= 0:
        duration = 5.0
    per_word = duration / len(known_words)
    return [
        {"word": w, "start": total_start + i * per_word, "end": total_start + (i + 1) * per_word}
        for i, w in enumerate(known_words)
    ]


def _burn_subtitles(source_path: str, timed_words: list[dict], output_path: str):
    """Burn animated subtitles: Arial Rounded Bold, Pop animation, 72fps.

    Style: WHITE BOLD UPPERCASE, YELLOW active word with pop scale.
    """
    chunks = [timed_words[i:i + 3] for i in range(0, len(timed_words), 3)]

    clip = VideoFileClip(source_path)
    vw, vh = clip.size
    y_pos = int(vh * 0.75)

    base_size = _find_font_size(chunks, vw)
    logger.info(f"Subtitle: video {vw}x{vh}, font size {base_size}px")

    static_cache = {}

    def make_frame(get_frame, t):
        frame = get_frame(t)

        for chunk in chunks:
            if chunk[0]["start"] <= t <= chunk[-1]["end"]:
                ai = -1
                for wi, wd in enumerate(chunk):
                    if wd["start"] <= t <= wd["end"]:
                        ai = wi
                        break
                if ai == -1:
                    for wi, wd in enumerate(chunk):
                        if t < wd["start"]:
                            ai = wi
                            break
                    if ai == -1:
                        ai = len(chunk) - 1

                anim = _anim_pop(t, chunk[ai]["start"], chunk[ai]["end"])
                is_static = abs(anim["scale"] - 1.0) < 0.005

                if is_static:
                    ck = (id(chunk), ai)
                    if ck not in static_cache:
                        static_cache[ck] = _render_chunk(chunk, ai, vw, vh, anim, base_size)
                    ti = static_cache[ck]
                else:
                    ti = _render_chunk(chunk, ai, vw, vh, anim, base_size)

                th, tw2 = ti.shape[:2]
                xo = max(0, (vw - tw2) // 2)
                yo = max(0, y_pos - th // 2)
                ye = min(vh, yo + th)
                xe = min(vw, xo + tw2)
                ha, wa = ye - yo, xe - xo

                alpha = ti[:ha, :wa, 3:4].astype(np.float32) / 255.0
                rgb = ti[:ha, :wa, :3].astype(np.float32)
                bg = frame[yo:ye, xo:xe].astype(np.float32)
                frame = frame.copy()
                frame[yo:ye, xo:xe] = (rgb * alpha + bg * (1.0 - alpha)).astype(np.uint8)
                break

        return frame

    result = clip.transform(make_frame)
    result.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=72,
        preset="medium",
        logger=None,
    )
    clip.close()
    result.close()


def add_subtitles(generation_id: int):
    """Full subtitle pipeline for a video generation."""
    db = SessionLocal()
    try:
        gen = db.query(VideoGeneration).get(generation_id)
        if not gen:
            logger.error(f"Subtitle: generation {generation_id} not found")
            return

        gen.subtitle_status = "processing"
        db.commit()

        dialogue_text = extract_dialogue(gen.prompt)
        if not dialogue_text:
            gen.subtitle_status = "failed"
            gen.subtitle_error = "No dialogue found in prompt"
            db.commit()
            return

        gen.subtitle_text = dialogue_text
        db.commit()

        base = os.path.join(DOWNLOADS_DIR, f"gen_{generation_id}")
        source_path = base + "_source.mp4"
        audio_path = base + "_audio.wav"
        output_path = base + "_subtitled.mp4"

        logger.info(f"Subtitle: downloading video for gen {generation_id}")
        urllib.request.urlretrieve(gen.video_url, source_path)

        logger.info(f"Subtitle: extracting audio for gen {generation_id}")
        subprocess.run([
            "ffmpeg", "-y", "-i", source_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path
        ], check=True, capture_output=True)

        logger.info(f"Subtitle: transcribing audio for gen {generation_id}")
        model = _get_whisper_model()
        result = model.transcribe(audio_path)

        whisper_words = []
        for segment in result.segments:
            for word in segment.words:
                whisper_words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                })

        known_words = dialogue_text.split()
        timed_words = _align_words(known_words, whisper_words)

        logger.info(f"Subtitle: burning subtitles for gen {generation_id}")
        _burn_subtitles(source_path, timed_words, output_path)

        gen.subtitled_video_path = output_path
        gen.subtitle_status = "completed"
        gen.subtitle_error = ""
        db.commit()
        logger.info(f"Subtitle: completed for gen {generation_id}")

        for f in [source_path, audio_path]:
            try:
                os.remove(f)
            except OSError:
                pass

    except Exception as e:
        logger.error(f"Subtitle pipeline failed for gen {generation_id}: {e}")
        try:
            gen = db.query(VideoGeneration).get(generation_id)
            if gen:
                gen.subtitle_status = "failed"
                gen.subtitle_error = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def add_subtitles_local(source_path: str, timed_words: list[dict], output_path: str):
    """Burn subtitles into a local video file (for testing without DB)."""
    _burn_subtitles(source_path, timed_words, output_path)
