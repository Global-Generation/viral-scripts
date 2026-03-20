import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Shared rules prepended to every V1 and V2
SHARED_RULES = """
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays.
ONLY the character sitting and talking. Nothing else on screen.

CAMERA — ONLY 3 ANGLES:
1. MEDIUM SHOT — character faces camera, upper body visible
2. CLOSE-UP — face fills the frame
3. OFFSET MEDIUM SHOT — camera slightly to the right, different part of the room visible, character still faces viewer

TRANSITIONS:
Only jump cut between shots. Format: --- jump cut ---

WORD BALANCE:
V1 and V2 dialogue word count must be roughly equal (±20%).

OUTPUT FORMAT (STRICT — follow this EXACTLY):
Each camera angle gets ONE line of brief description, then dialogue in quotes on the next line.
Between angles, write --- jump cut --- on its own line.
NO continuous prose. NO body language paragraphs. NO energy descriptions.
Keep it minimal — angle name + short description, then dialogue.

Example format:
MEDIUM SHOT — The character sits composed, facing camera with calm authority.
"First line of dialogue here."
--- jump cut ---
CLOSE-UP — Eyes locked on camera, measured intensity.
"Second line of dialogue here."
--- jump cut ---
OFFSET MEDIUM SHOT — Camera slightly right, different part of the room visible.
"Third line of dialogue here."

RULES:
- Use EXACT phrases from the script. Do NOT paraphrase or invent new dialogue
- Each video should have 2-3 camera angles with jump cuts between them
- Same angle twice in a row = FORBIDDEN
- All cameras are FIXED. STATIC. No movement words (pan, zoom, dolly, push, pull, drift, track, orbit, glide, sweep, arc, slide, follow)
- Split script into 2 videos SEQUENTIALLY with roughly equal text
- Always split at a SENTENCE BOUNDARY — never mid-sentence"""

# ── STEP 1: Video 1 (first half of script) ──

SYSTEM_VIDEO1 = f"""You are a video prompt writer for short-form vertical content.
You generate a SINGLE video prompt — Video 1 of 2.

{SHARED_RULES}

VIDEO 1 uses the first ~50% of the script words.
The LAST quoted line must be a COMPLETE SENTENCE.

IMPORTANT — V1 ENDING ANGLE:
Note which angle V1 ends on. V2 MUST start on a DIFFERENT angle for seamless splicing."""

USER_VIDEO1 = """Generate Video 1 of 2 from this script.

Prepend this line at the top of your output:
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays. ONLY the character sitting and talking. Nothing else on screen.

Use ONLY the first ~50% of the script as dialogue. Leave the rest for Video 2.
Use the exact minimal format: angle + brief description, dialogue in quotes, --- jump cut --- between angles.
NO prose paragraphs. NO body language descriptions. NO energy arcs.

YOUR HALF OF THE SCRIPT ({word_count} words):
{script}"""

# ── STEP 2: Video 2 (second half of script) ──

SYSTEM_VIDEO2 = f"""You are a video prompt writer for short-form vertical content.
You generate a SINGLE video prompt — Video 2 of 2.

{SHARED_RULES}

VIDEO 2 uses the remaining ~50% of the script words.
End with a simple CTA: "Link in bio." (counts toward word balance).

V1 → V2 SPLICE RULE (CRITICAL):
V2 MUST start on a DIFFERENT angle than V1 ended on.
This makes the splice between videos seamless."""

USER_VIDEO2 = """Generate Video 2 of 2 from this script.

Prepend this line at the top of your output:
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays. ONLY the character sitting and talking. Nothing else on screen.

Pick up EXACTLY where Video 1 left off. Zero overlap. Do NOT repeat any V1 dialogue.
Use the exact minimal format: angle + brief description, dialogue in quotes, --- jump cut --- between angles.
NO prose paragraphs. NO body language descriptions. NO energy arcs.
End with "Link in bio." as the last line of dialogue.

VIDEO 1 ENDED ON THIS ANGLE (start V2 on a DIFFERENT angle):
{v1_last_angle}

VIDEO 1 ALREADY GENERATED (DO NOT REPEAT):
{video1}

YOUR HALF OF THE SCRIPT:
{script}"""


def _log_usage(request_type: str, status: str = "completed"):
    try:
        from database import SessionLocal
        from models import ApiUsage
        db = SessionLocal()
        db.add(ApiUsage(platform="anthropic", model_id=CLAUDE_MODEL, request_type=request_type, status=status))
        db.commit()
        db.close()
    except Exception:
        pass


def _strip_label(text: str, video_num: int) -> str:
    """Strip 'VIDEO N:' label and word count tag if AI adds them."""
    import re
    for prefix in (f"VIDEO {video_num}:", f"VIDEO {video_num} —", f"VIDEO {video_num}:"):
        if text.upper().startswith(prefix.upper()):
            text = text[len(prefix):].strip()
            break
    if "SPLICE STATE:" in text:
        text = text.split("SPLICE STATE:", 1)[0].strip()
    text = re.sub(r'\[DIALOGUE WORD COUNT:\s*\d+\]', '', text).strip()
    return text


def _detect_last_angle(prompt_text: str) -> str:
    """Detect the last camera angle used in a video prompt."""
    text_upper = prompt_text.upper()
    last_angle = "MEDIUM SHOT"
    last_pos = -1
    for angle in ("MEDIUM SHOT", "CLOSE-UP", "OFFSET MEDIUM SHOT"):
        pos = text_upper.rfind(angle)
        if pos > last_pos:
            last_pos = pos
            last_angle = angle
    return last_angle


def generate_video_prompt(script_text: str) -> dict:
    """Return {"video1": ..., "video2": ...} — each is a standalone filming prompt."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    words = script_text.split()
    word_count = len(words)
    half = word_count // 2

    first_half = " ".join(words[:half])
    second_half = " ".join(words[half:])

    # Step 1: Generate Video 1
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(
            script=first_half, word_count=len(words[:half])
        )}]
    )
    video1_text = _strip_label(response1.content[0].text.strip(), 1)

    # Detect V1's last angle so V2 starts on a different one
    v1_last_angle = _detect_last_angle(video1_text)

    # Step 2: Generate Video 2
    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(
            script=second_half, video1=video1_text, v1_last_angle=v1_last_angle
        )}]
    )
    video2_text = _strip_label(response2.content[0].text.strip(), 2)

    _log_usage("prompt")
    _log_usage("prompt")
    return {
        "video1": video1_text,
        "video2": video2_text,
        "video3": "",
    }
