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

WORD BALANCE (STRICT — THIS IS A HARD RULE):
V1 and V2 dialogue word count MUST be within ±20% of each other.
Example: if V1 has 30 words of dialogue, V2 must have 24-36 words.
FORBIDDEN: V2 having less than half the dialogue of V1. Count your words and rebalance if needed.

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

CAMERA COUNT PER VIDEO (STRICT):
Each video has EXACTLY 2 camera angles with 1 jump cut between them. NOT 3. NOT 4. Just 2.

RULES:
- Use EXACT phrases from the script. Do NOT paraphrase or invent new dialogue
- Same angle twice in a row = FORBIDDEN
- All cameras are FIXED. STATIC. No movement words (pan, zoom, dolly, push, pull, drift, track, orbit, glide, sweep, arc, slide, follow)
- Split script into 2 videos SEQUENTIALLY with roughly equal text
- Always split at a SENTENCE BOUNDARY — never mid-sentence"""

# ── STEP 1: Video 1 (first half of script) ──

SYSTEM_VIDEO1 = f"""You are a video prompt writer for short-form vertical content.
You generate a SINGLE video prompt — Video 1 of 2.

{SHARED_RULES}

VIDEO 1 uses the first ~50% of the script words.
V1 dialogue MUST end on a complete sentence. NEVER cut mid-thought.
The LAST quoted line must be a COMPLETE SENTENCE ending with . ! or ?
ABSOLUTELY FORBIDDEN: ending V1 dialogue with an incomplete thought like "Lost" or "That's when I" — the last word of V1 must complete a full sentence grammatically and logically. If needed, move extra text to V2 rather than cutting mid-sentence.
WORD COUNT: Your V1 dialogue must be CLOSE to the target word count given. Do not go far over or under.

IMPORTANT — V1 ENDING ANGLE:
Note which angle V1 ends on. V2 MUST start on a DIFFERENT angle for seamless splicing."""

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
V2 MUST start on a DIFFERENT angle than V1 ended on.
This makes the splice between videos seamless."""

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
    """Pick 2 different angle pairs for V1 and V2 so they never repeat across videos."""
    import random
    angles = ["MEDIUM SHOT", "CLOSE-UP", "OFFSET MEDIUM SHOT"]
    # All possible 2-angle pairs (order matters)
    pairs = [(a, b) for a in angles for b in angles if a != b]
    # Pick V1 pair randomly
    v1_pair = random.choice(pairs)
    # V2 must start on a different angle than V1 ends on
    v2_candidates = [(a, b) for a, b in pairs if a != v1_pair[1]]
    v2_pair = random.choice(v2_candidates)
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

        # Check word balance
        v2_dialogue_words = sum(len(m.split()) for m in re.findall(r'"([^"]+)"', video2_text))
        if v1_dialogue_words == 0 or v1_min <= v2_dialogue_words <= v1_max:
            break
        ratio = v2_dialogue_words / v1_dialogue_words * 100
        logger.warning(f"V2 word balance off ({ratio:.0f}%): V1={v1_dialogue_words}w V2={v2_dialogue_words}w, retry {attempt+1}/2")

    _log_usage("prompt")
    return {
        "video1": video1_text,
        "video2": video2_text,
        "video3": "",
    }
