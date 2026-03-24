import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Shared rules prepended to every V1 and V2
SHARED_RULES = """
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays.
ONLY the character sitting and talking. Nothing else on screen.

STYLE — UGC / AUTHENTIC (CRITICAL):
This must look like REAL user-generated content. Raw, unpolished, authentic.
- Character talks directly to camera like filming themselves on a phone
- Natural lighting, real rooms, NOT a studio
- Each angle MUST describe a DIFFERENT outfit and DIFFERENT background/room
- This creates the feel of clips filmed on different days — maximum authenticity
- The character's DISTANCE FROM CAMERA stays the SAME across all angles (consistent framing)
- Pose changes between angles: different hand position, different lean, different energy

CAMERA — ONLY 3 ANGLES:
1. MEDIUM SHOT — character faces camera, upper body visible
2. CLOSE-UP — face fills the frame
3. OFFSET MEDIUM SHOT — camera slightly to the right, different part of the room visible, character still faces viewer

TRANSITIONS:
Only jump cut between shots. Format: --- jump cut ---

WORD BALANCE (STRICT — THIS IS A HARD RULE):
V1 and V2 dialogue word count MUST be within ±20% of each other.
Example: if V1 has 30 words of dialogue, V2 must have 24-36 words.
FORBIDDEN: V2 having less than half the dialogue of V1. Count your words and rebalance if needed.

OUTPUT FORMAT (STRICT — follow this EXACTLY):
Each camera angle gets ONE line of brief description, then dialogue in quotes on the next line.
Between angles, write --- jump cut --- on its own line.
NO continuous prose. NO body language paragraphs. NO energy descriptions.
Keep it minimal — angle name + short description, then dialogue.
IMPORTANT: Each angle description MUST mention a DIFFERENT outfit and DIFFERENT room/background.

Example format:
MEDIUM SHOT — The character in a navy blazer sits in a home office, bookshelves behind, facing camera.
"First line of dialogue here."
--- jump cut ---
CLOSE-UP — Now in a grey sweater, different room with warm lighting, eyes locked on camera.
"Second line of dialogue here."

CAMERA COUNT PER VIDEO (STRICT):
Each video has EXACTLY 2 camera angles with 1 jump cut between them. NOT 3. NOT 4. Just 2.

RULES:
- Use EXACT phrases from the script. Do NOT paraphrase or invent new dialogue
- Same angle twice in a row = FORBIDDEN
- All cameras are FIXED. STATIC. No movement words (pan, zoom, dolly, push, pull, drift, track, orbit, glide, sweep, arc, slide, follow)
- Split script into 2 videos SEQUENTIALLY with roughly equal text
- Always split at a SENTENCE BOUNDARY — never mid-sentence
- EVERY angle = different outfit + different background. This is NOT optional."""

# ── STEP 1: Video 1 (first half of script) ──

SYSTEM_VIDEO1 = f"""You are a video prompt writer for short-form vertical content.
You generate a SINGLE video prompt — Video 1 of 2.

{SHARED_RULES}

VIDEO 1 uses the first ~50% of the script words.
V1 dialogue MUST end on a complete sentence. NEVER cut mid-thought.
The LAST quoted line must be a COMPLETE SENTENCE ending with . ! or ?
ABSOLUTELY FORBIDDEN: ending V1 dialogue with an incomplete thought like "Lost" or "That's when I" — the last word of V1 must complete a full sentence grammatically and logically. If needed, move extra text to V2 rather than cutting mid-sentence.
WORD COUNT: Your V1 dialogue must be CLOSE to the target word count given. Do not go far over or under.

IMPORTANT — V1 CAMERA RULE (STRICT):
- First angle is ALWAYS MEDIUM SHOT — use it for the FIRST SENTENCE ONLY
- After the first sentence, jump cut to OFFSET MEDIUM SHOT (side view, camera ~30° to the right) for ALL remaining dialogue
- This creates an immediate visual hook — the camera shift right after the opening line
- V1 ALWAYS ends on OFFSET MEDIUM SHOT. V2 MUST start on a DIFFERENT angle for seamless splicing."""

USER_VIDEO1 = """Generate Video 1 of 2 from this script.

Prepend this line at the top of your output:
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays. ONLY the character sitting and talking. Nothing else on screen.

Use ONLY the first ~50% of the script as dialogue. Leave the rest for Video 2.
Use the exact minimal format: angle + brief description, dialogue in quotes, --- jump cut --- between angles.
NO prose paragraphs. NO body language descriptions. NO energy arcs.

TARGET DIALOGUE WORD COUNT: ~{target_words} words (this is half the total script). Stay close to this number.

ANGLE PAIR FOR THIS VIDEO (use exactly these 2 angles in this order):
{v1_angle_pair}

FULL SCRIPT ({word_count} words total — use ONLY the first ~{target_words} words as dialogue):
{script}"""

# ── STEP 2: Video 2 (second half of script) ──

SYSTEM_VIDEO2 = f"""You are a video prompt writer for short-form vertical content.
You generate a SINGLE video prompt — Video 2 of 2.

{SHARED_RULES}

VIDEO 2 uses the remaining ~50% of the script words. Use ALL of them — do NOT cut or shorten.
End with a simple CTA: "Link in bio." (counts toward word balance).
V2 dialogue word count MUST be within ±20% of V1. If V1 had ~30 words, V2 must have 24-36 words. Do NOT make V2 shorter than V1.

V1 → V2 SPLICE RULE (CRITICAL):
V2 ALWAYS starts on MEDIUM SHOT (general plan) — this is different from V1's ending angle (OFFSET).
Then jump cut to CLOSE-UP or OFFSET MEDIUM SHOT. V2 must NOT end on MEDIUM SHOT."""

USER_VIDEO2 = """Generate Video 2 of 2 from this script.

Prepend this line at the top of your output:
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays. ONLY the character sitting and talking. Nothing else on screen.

Pick up EXACTLY where Video 1 left off. Zero overlap. Do NOT repeat any V1 dialogue.
Use the exact minimal format: angle + brief description, dialogue in quotes, --- jump cut --- between angles.
NO prose paragraphs. NO body language descriptions. NO energy arcs.
End with "Link in bio." as the last line of dialogue.

CRITICAL WORD COUNT TARGET: Video 1 has {v1_word_count} words of dialogue. Your V2 dialogue MUST have {v1_min_words}-{v1_max_words} words (±20%). Count carefully. Use ALL the script text below.

ANGLE PAIR FOR THIS VIDEO (use exactly these 2 angles in this order):
{v2_angle_pair}

VIDEO 1 ALREADY GENERATED (DO NOT REPEAT):
{video1}

FULL SCRIPT (use ONLY the part after where V1 stopped — do NOT repeat V1 dialogue):
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


def _detect_first_angle(prompt_text: str) -> str:
    """Detect the first camera angle used in a video prompt."""
    text_upper = prompt_text.upper()
    first_angle = "MEDIUM SHOT"
    first_pos = len(text_upper)
    for angle in ("MEDIUM SHOT", "CLOSE-UP", "OFFSET MEDIUM SHOT"):
        pos = text_upper.find(angle)
        if 0 <= pos < first_pos:
            first_pos = pos
            first_angle = angle
    return first_angle


def _split_at_sentence_boundary(text: str) -> tuple[str, str]:
    """Split text into two halves at nearest sentence boundary to 50%."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) < 2:
        # Fallback: can't split by sentence, return as-is
        words = text.split()
        half = len(words) // 2
        return " ".join(words[:half]), " ".join(words[half:])

    total_words = len(text.split())
    target = total_words // 2

    current_words = 0
    best_split = 1  # at least 1 sentence in first half
    best_diff = total_words

    for i, sentence in enumerate(sentences):
        current_words += len(sentence.split())
        diff = abs(current_words - target)
        if diff < best_diff:
            best_diff = diff
            best_split = i + 1

    first_half = " ".join(sentences[:best_split])
    second_half = " ".join(sentences[best_split:])
    return first_half, second_half


def _pick_angle_pairs():
    """Pick angle pairs for V1 and V2.
    V1: MEDIUM SHOT → OFFSET MEDIUM SHOT (side view ~30°)
    V2: MEDIUM SHOT → random(CLOSE-UP, OFFSET MEDIUM SHOT)
    Neither video ends on MEDIUM SHOT."""
    import random
    v1_pair = ("MEDIUM SHOT", "OFFSET MEDIUM SHOT")
    v2_pair = ("MEDIUM SHOT", random.choice(["CLOSE-UP", "OFFSET MEDIUM SHOT"]))
    return v1_pair, v2_pair


def generate_video_prompt(script_text: str) -> dict:
    """Return {"video1": ..., "video2": ...} — each is a standalone filming prompt."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    first_half, second_half = _split_at_sentence_boundary(script_text)

    # Pick random angle pairs — different for each script, splice-safe
    v1_pair, v2_pair = _pick_angle_pairs()
    v1_angle_str = f"1. {v1_pair[0]}\n2. {v1_pair[1]}"
    v2_angle_str = f"1. {v2_pair[0]}\n2. {v2_pair[1]}"

    # Step 1: Generate Video 1
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        temperature=0.3,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(
            script=script_text, word_count=len(script_text.split()),
            target_words=len(script_text.split()) // 2,
            v1_angle_pair=v1_angle_str
        )}]
    )
    video1_text = _strip_label(response1.content[0].text.strip(), 1)

    # Count V1 dialogue words to enforce balance in V2
    import re
    v1_dialogue_words = sum(len(m.split()) for m in re.findall(r'"([^"]+)"', video1_text))
    v1_min = max(1, int(v1_dialogue_words * 0.8))
    v1_max = int(v1_dialogue_words * 1.2)

    # Step 2: Generate Video 2 (with up to 2 retries for word balance)
    video2_text = None
    for attempt in range(3):
        # Use higher temperature on retries to get different output
        temp = 0.3 if attempt == 0 else 0.7 + attempt * 0.1
        response2 = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=700,
            temperature=temp,
            system=SYSTEM_VIDEO2,
            messages=[{"role": "user", "content": USER_VIDEO2.format(
                script=script_text, video1=video1_text,
                v2_angle_pair=v2_angle_str,
                v1_word_count=v1_dialogue_words,
                v1_min_words=v1_min,
                v1_max_words=v1_max
            )}]
        )
        video2_text = _strip_label(response2.content[0].text.strip(), 2)
        _log_usage("prompt")

        # Check word balance and angle
        v2_dialogue_words = sum(len(m.split()) for m in re.findall(r'"([^"]+)"', video2_text))
        v2_first = _detect_first_angle(video2_text)
        word_ok = v1_dialogue_words == 0 or v1_min <= v2_dialogue_words <= v1_max
        angle_ok = v2_first == "MEDIUM SHOT"
        if word_ok and angle_ok:
            break
        if not angle_ok:
            logger.warning(f"V2 starts with {v2_first} instead of MEDIUM SHOT, retry {attempt+1}/2")
        if not word_ok:
            ratio = v2_dialogue_words / v1_dialogue_words * 100
            logger.warning(f"V2 word balance off ({ratio:.0f}%): V1={v1_dialogue_words}w V2={v2_dialogue_words}w, retry {attempt+1}/2")

    _log_usage("prompt")
    return {
        "video1": video1_text,
        "video2": video2_text,
        "video3": "",
    }


def generate_video2_only(script_text: str, existing_v1: str) -> str:
    """Regenerate only Video 2 using the existing Video 1 prompt."""
    import re, random
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    v2_pair = ("MEDIUM SHOT", random.choice(["CLOSE-UP", "OFFSET MEDIUM SHOT"]))
    v2_angle_str = f"1. {v2_pair[0]}\n2. {v2_pair[1]}"

    v1_dialogue_words = sum(len(m.split()) for m in re.findall(r'"([^"]+)"', existing_v1))
    v1_min = max(1, int(v1_dialogue_words * 0.8))
    v1_max = int(v1_dialogue_words * 1.2)

    video2_text = None
    for attempt in range(3):
        temp = 0.3 if attempt == 0 else 0.7 + attempt * 0.1
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=700,
            temperature=temp,
            system=SYSTEM_VIDEO2,
            messages=[{"role": "user", "content": USER_VIDEO2.format(
                script=script_text, video1=existing_v1,
                v2_angle_pair=v2_angle_str,
                v1_word_count=v1_dialogue_words,
                v1_min_words=v1_min,
                v1_max_words=v1_max
            )}]
        )
        video2_text = _strip_label(response.content[0].text.strip(), 2)
        _log_usage("prompt_v2_regen")

        v2_first = _detect_first_angle(video2_text)
        if v2_first == "MEDIUM SHOT":
            break
        logger.warning(f"V2 regen starts with {v2_first}, retry {attempt+1}/2")

    return video2_text
