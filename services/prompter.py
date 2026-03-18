import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Shared rules included in all steps
SHARED_RULES = """
CHARACTER & LOCATION
- Character is ALWAYS MALE (he/him/his). Drop any female names/pronouns from script
- Appearance, clothing, setting, frame format — ALL from reference photo. Do NOT describe in text
- Sits in one location. Does not stand or walk
- Natural gesticulation: object in hands, fingers, palms, lean forward/back, head tilts, nods
- Face ALWAYS in frame
- No B-roll. No numbers/text on screen. No location changes
- Frame is VERTICAL 9:16

GESTICULATION BY EMOTION:
- Authority → finger/object toward camera, palm on table
- Sarcasm → counts on fingers, raises eyebrow
- Empathy → open palms, lean forward
- Impact → pause, direct gaze, nod

CAMERA — EXACTLY THREE SHOT TYPES (NO OTHERS!)
Only these 3 angles exist. No other angles, no variations, no invented shots.
Alternate STRICTLY. Same angle twice in a row = FORBIDDEN.

CLOSE-UP:
Face fills the entire frame. Camera frontal, at eye level.
Only face, neck, top of shoulders visible. Background out of focus — bookshelves/diplomas barely readable.
Direct eye contact with camera. Used for emotional hits, pauses, main point delivery.

MEDIUM SHOT:
Upper body — chest to head. Camera frontal, slightly wider than close-up.
Hands visible — pen in hand, gesticulation, pointing. Background readable (diplomas, lamp, bookshelves).
Main working angle for dialogue and active gesturing.

WIDE THREE-QUARTER:
Camera shifted to the side — approximately 30-45° angle, pulled back.
Full setting visible: armchair, side table, bookshelves, window with city view.
Character occupies ~40% of frame, seated in armchair. Used for lists, pauses, "exhale" moments.

CAMERA CUTS (CRITICAL — NO SMOOTH CAMERA MOVEMENTS!)
All three cameras are FIXED on tripods. COMPLETELY STATIC. Zero movement within any shot.
All transitions are HARD CUTS — instant switch from one static angle to another.
Every transition = "JUMP CUT TO close-up." or "JUMP CUT TO medium shot." or "JUMP CUT TO three-quarter view." — PERIOD.
NEVER use these words FOR THE CAMERA: orbit, dolly, drift, push-in, pull-out, track, pan, slide, creep, arc, zoom, push, pull, glide, sweep, follow, close in, move closer, slowly pushes, pulls back.
The CAMERA does not move. The CHARACTER moves freely (gestures, lean, nod, turn, expressions).

STRUCTURE OF EACH VIDEO:
HOOK (opening) — medium shot, direct gaze, first phrase
DEVELOPMENT — alternate close-up ↔ wide 3/4 ↔ medium
TURN — energy shift, close-up → medium
HIT — close-up, main point, pause, direct gaze
FINALE — medium or wide 3/4 (vary each time)

TEXT RULES:
- ~20-25 words of dialogue per video. If script text is longer — shorten, preserve meaning
- Dialogue chunks between camera changes must be EQUAL LENGTH (1-2 sentences each)
- Use EXACT phrases from the original script. Do NOT paraphrase, rewrite, or invent new dialogue

DIALOGUE WORD LIMIT:
Each video gets EXACTLY 20-25 words of dialogue. NOT 30. NOT 40.
After writing, COUNT every word inside "quotes". If more than 25 — DELETE lines until 20-25.
VERIFICATION: write at the end: [DIALOGUE WORD COUNT: XX]
If XX > 25, you have FAILED. Go back and cut.

OUTPUT FORMAT:
Each prompt contains:
1. Camera rules (shot alternation, transitions)
2. Energy type (rising / resolving)
3. Continuous scene description with dialogue in "quotes"

Character, location, frame format, resolution — all from reference photo. Do NOT duplicate in text.
Format — continuous text as a directorial scene description. No lists, no timecodes.
Describe body language, expressions, energy between dialogue lines — be specific and visual.

SPLITTING RULE (CRITICAL — SEQUENTIAL FILL):
The script is split into 2 videos SEQUENTIALLY, with EQUAL text in each:
1. Video 1 = first ~50% of the script words (HOOK + DEVELOPMENT)
2. Video 2 = remaining ~50% of the script words (CONCLUSION + CTA)
Each video uses EXACT lines from the script in order. No skipping, no rearranging.
The two halves must be APPROXIMATELY EQUAL in dialogue word count (within 3 words of each other)."""

# ── STEP 1: Video 1 (HOOK — problem, tension rising) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 2 (HOOK + DEVELOPMENT).

{SHARED_RULES}

ENERGY — VIDEO 1 = PROBLEM
Energy RISES from start to end.
Start — calm tone, minimal gestures, direct gaze.
Middle — voice strengthens, gesticulation appears, lean forward.
End — energy at peak, body tense, leaning forward.
Speech pace accelerates toward the end.
The LAST line of dialogue must be a COMPLETE sentence — no mid-word or mid-phrase cuts.

SPLICE POINT (CRITICAL — VIDEO 1 ENDING):
Video 1 ends with the last thought FINISHED — the sentence lands cleanly.
After the final word, describe a PAUSE BEAT (1-2 seconds of silence):
- Character holds direct gaze into camera
- Slight nod or settled expression — energy is high but the moment lands
- Body still, leaning forward, no movement
This pause IS the splice point. Describe the EXACT angle, pose, and energy
level during the pause — Video 2 must open from this identical state.

"""

USER_VIDEO1 = """Generate Video 1 of 2 (HOOK + DEVELOPMENT) from this script.
Use ONLY the first ~50% of the script as dialogue. STOP at the halfway point — leave the rest for Video 2.
Do NOT paraphrase or invent new lines. Do NOT include the conclusion or payoff.
2-3 camera changes (HARD CUTS only — static tripod angles). Energy rises from calm to peak tension.
Describe body language, expressions, and energy between dialogue lines — be specific and visual.

CRITICAL: EXACTLY 20-25 words of dialogue total in this video. Count every word inside "quotes".
If you write more than 25 words of dialogue, DELETE lines until 20-25.
At the end of your output, write: [DIALOGUE WORD COUNT: XX]

---

YOUR HALF OF THE SCRIPT ({word_count} words — use ALL of these as dialogue, nothing else):
{script}"""

# ── STEP 2: Video 2 (RESOLUTION — payoff) ──

SYSTEM_VIDEO2 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 2 of 2 (CONCLUSION + CTA).

{SHARED_RULES}

ENERGY — VIDEO 2 = SOLUTION
Energy does NOT reset at start.
Energy stays elevated but shifts quality — from tension to confidence.
Middle — calm listing, open palms.
End — HIT: main point, close-up, direct gaze, nod, silence. Feeling of PERIOD. Everything said.

SPLICE POINT (CRITICAL — VIDEO 2 OPENING):
Video 2 opens with a PAUSE BEAT (1-2 seconds of silence) that matches V1's ending:
- SAME camera angle (match V1's last shot exactly)
- SAME body pose (same position, same lean)
- SAME energy level (do NOT reset, do NOT restart)
- SAME facial expression (same emotion, same gaze)
During this opening pause the character is still, settled, holding the beat.
THEN the character begins speaking — launching into the resolution.
The transition is: pause → exhale → first word. Energy gradually shifts from tension to confidence.
In your prompt, EXPLICITLY describe the opening pause state: which angle, which pose, which energy.

CTA (MANDATORY — EXACT PATTERN!):
The LAST thing he says is a simple CTA. Use ONLY one of these patterns:
- "I share more tips like this — link in bio."
- "More advice on my page — link in bio."
- "Follow for more — link in bio."
NEVER invent creative CTAs. NEVER say "comment [word]". NEVER mention apps, products, or tools.
Just: he gives advice → link in bio. That's it. This counts toward the word limit.

ENDING:
End with quiet finality. The LAST shot should be a CLOSE-UP with a nod after CTA."""

USER_VIDEO2 = """Generate Video 2 of 2 (CONCLUSION + CTA) from this script.
Pick up EXACTLY where Video 1 left off. Do NOT repeat ANY line from Video 1. Zero overlap.
Use EXACT remaining lines from the script as dialogue — do NOT paraphrase. End with CTA.
2-3 camera changes (HARD CUTS only — static tripod angles). Start from the SAME state as Video 1 ended, then resolve.
Describe body language, expressions, and energy between dialogue lines — be specific and visual.

CRITICAL: EXACTLY 20-25 words of dialogue total in this video — SAME amount as Video 1. Count every word inside "quotes".
CTA counts toward the word limit. If you write more than 25 words of dialogue, DELETE lines until 20-25.
At the end of your output, write: [DIALOGUE WORD COUNT: XX]

---

VIDEO 1 ALREADY GENERATED (DO NOT REPEAT ANY OF THIS):
{video1}

---

YOUR HALF OF THE SCRIPT (use ONLY these words as dialogue):
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
    for prefix in (f"VIDEO {video_num}:", f"VIDEO {video_num} —", f"VIDEO {video_num}:"):
        if text.upper().startswith(prefix.upper()):
            text = text[len(prefix):].strip()
            break
    if "SPLICE STATE:" in text:
        text = text.split("SPLICE STATE:", 1)[0].strip()
    # Strip [DIALOGUE WORD COUNT: XX] tag
    import re
    text = re.sub(r'\[DIALOGUE WORD COUNT:\s*\d+\]', '', text).strip()
    return text


def generate_video_prompt(script_text: str) -> dict:
    """Return {"video1": ..., "video2": ...} — each is a standalone filming prompt (2 equal-length parts)."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    words = script_text.split()
    word_count = len(words)
    half = word_count // 2  # 50/50 split

    # Pre-split script into 2 halves — Claude only sees its half
    first_half = " ".join(words[:half])
    second_half = " ".join(words[half:])
    half_words = half

    # Step 1: Generate Video 1 (Hook + Development — first half ONLY)
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(
            script=first_half, word_count=len(words[:half]), half_words=half_words
        )}]
    )
    video1_text = _strip_label(response1.content[0].text.strip(), 1)

    # Step 2: Generate Video 2 (Conclusion + CTA — second half ONLY)
    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(
            script=second_half, video1=video1_text
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
