import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Shared rules included in all steps
SHARED_RULES = """
══════════════════════
CHARACTER & LOCATION
══════════════════════
- The character is ALWAYS MALE. Use masculine pronouns (he/him/his). Remove any female names, references, or pronouns from the original script
- If the original script mentions a female name (e.g. "Sabrina", "Jessica") — DROP IT completely or replace with a neutral phrase. NEVER keep female names or say "she/her"
- Appearance, clothing, setting, frame format — ALL from the reference photo and generator settings. Do NOT describe in text
- Character sits in one location. Does not stand up or walk
- Natural gesticulation: object in hands, fingers, palms, lean forward/back, head tilts, nods — all OK. The CHARACTER moves freely, the CAMERA does not
- Face ALWAYS in frame
- No B-roll. No numbers/text on screen. No location changes
- Frame is VERTICAL 9:16 — always cropped to portrait orientation

GESTICULATION BY EMOTION:
- Authority → finger/object toward camera, palm on table
- Sarcasm → counts on fingers, raises eyebrow
- Empathy → open palms, lean forward
- Impact → pause, direct gaze, nod

══════════════════════
CAMERA
══════════════════════
Three framing types. ALL THREE must appear in every video. NEVER repeat the same angle twice in a row.

1. MEDIUM SHOT — front-facing, chest to head, hands visible gesticulating, room behind. Good opening shot.
2. THREE-QUARTER VIEW — camera at 30-45° from front (NOT side profile), wider framing, full upper body + room/furniture visible.
3. CLOSE-UP — front-facing, face fills frame from shoulders up, direct eye contact. Best for impact moments.

Recommended sequence: medium → three-quarter → close-up, or three-quarter → medium → close-up.
Do NOT start with close-up — it's too abrupt. Save close-up for the strongest line or the ending.

══════════════════════
CAMERA CUTS (CRITICAL — NO SMOOTH MOVEMENTS!)
══════════════════════
Three angles — close-up (front), medium shot (front), three-quarter view (30-45° angle, NOT side profile).
All cameras are FIXED on tripods. COMPLETELY STATIC. Zero movement within any shot.
All transitions are HARD CUTS — instant switch from one static angle to another static angle.

Every transition = just "JUMP CUT TO close-up." or "JUMP CUT TO three-quarter view." — PERIOD. That's it.
Do NOT add descriptions after the cut. Just "JUMP CUT TO [angle]." on its own line.
The dialogue goes on the NEXT line after the cut.
NEVER use these words FOR THE CAMERA: orbit, dolly, drift, push-in, pull-out, track, pan, slide, creep, arc, zoom, push, pull, glide, sweep, follow, close in, move closer.
Each angle is a FROZEN STATIC FRAME — the CAMERA does not move within a shot. The CHARACTER can move freely (gestures, lean, nod, turn).

══════════════════════
HOOK — FIRST 2 SECONDS
══════════════════════
The opening should feel natural and confident, NOT screaming or panicking.
Options (vary between scripts):
- Start on close-up, then JUMP CUT TO three-quarter view
- Start on three-quarter view, then JUMP CUT TO close-up
- Start on medium shot, mid-gesture, then CUT TO three-quarter view
First CUT = quick angle switch. But the CHARACTER stays calm.

══════════════════════
TONE (CRITICAL!)
══════════════════════
- The character speaks with CALM CONFIDENCE — like a smart friend explaining something over coffee
- NO yelling, NO panic, NO "STOP SCROLLING", NO fake shock, NO "WHAT THE HELL"
- NO exclamation marks in dialogue unless truly warranted
- NO words like: insane, crazy, mind-blowing, terrifying, shocking, unbelievable
- Body language: relaxed authority — lean back, measured gestures, occasional lean forward for emphasis
- Voice: conversational, steady, matter-of-fact. Drops quieter for impact, never louder
- Think: podcast host who knows his stuff, NOT a hype beast

══════════════════════
OUTPUT FORMAT
══════════════════════
Character, location, frame format, resolution — all from reference photo. Do NOT describe.
Format — continuous text as a directorial scene description. No lists, no timecodes.
DIALOGUE: Use EXACT phrases from the original script. Do NOT paraphrase, rewrite, or invent new dialogue. Pick the strongest lines and quote them word-for-word.

⚠️⚠️⚠️ ABSOLUTE WORD LIMIT — READ THIS THREE TIMES ⚠️⚠️⚠️
THIS VIDEO gets EXACTLY 25-30 words of dialogue. NOT 40. NOT 50. NOT 60.
BEFORE you write, COUNT the dialogue words in the original script, divide by 2, and use ONLY that many.
After writing, COUNT every word inside "quotes". If you have more than 30 dialogue words, DELETE lines until you're at 25-30.
VERIFICATION STEP: List the count at the end like this: [DIALOGUE WORD COUNT: XX]
If XX > 30, you have FAILED. Go back and cut.
⚠️⚠️⚠️ END WORD LIMIT ⚠️⚠️⚠️

2-3 camera changes per video. Do NOT cut on every line — group multiple dialogue lines into one shot.
Between camera changes: ONLY the dialogue in quotes. No descriptions of emotions, expressions, tone, posture, gaze, atmosphere, or body language. The ONLY allowed actions are: "He pauses.", "He nods.", "Silence." — nothing else. Example format:

JUMP CUT TO three-quarter view.

"Dialogue goes here."

JUMP CUT TO close-up.

"Next dialogue line."
SPLITTING RULE (CRITICAL — SEQUENTIAL FILL):
The script is split into 2 videos SEQUENTIALLY, with EQUAL text in each:
1. Video 1 = first ~50% of the script words (HOOK + DEVELOPMENT)
2. Video 2 = remaining ~50% of the script words (CONCLUSION + CTA)
Each video uses EXACT lines from the script in order. No skipping, no rearranging.
The two halves must be APPROXIMATELY EQUAL in dialogue word count (within 5 words of each other)."""

# ── STEP 1: Video 1 (HOOK — problem, tension rising) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 2 (HOOK + DEVELOPMENT).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = HOOK + DEVELOPMENT
══════════════════════
Use ONLY the first ~50% of the script. Stop at roughly the halfway point.
HARD LIMIT: ~30 words of dialogue max in this video. Total across both videos = 60 words max.
Character stays composed. Never frantic.
The conclusion, moral, and payoff belong in Video 2.
End mid-story on a COMPLETE SENTENCE. The viewer wants to hear what comes next.

══════════════════════
ENDING (MANDATORY!)
══════════════════════
Video 1 ends on a COMPLETE SENTENCE. The thought is finished grammatically, but the topic is left open.
The LAST shot of Video 1 must be a CLOSE-UP — this is the splice point where Video 2 will be joined.
The VERY LAST LINE of Video 1 must ALWAYS be: He pauses.
This is NON-NEGOTIABLE. Every Video 1 ends with "He pauses." — no exceptions. No long silence.

"""

USER_VIDEO1 = """Generate Video 1 of 2 (HOOK + DEVELOPMENT) from this script.
Use ONLY the first ~50% of the script as dialogue. STOP at the halfway point — leave the rest for Video 2.
Do NOT paraphrase or invent new lines. Do NOT include the conclusion or payoff.
2-3 camera changes. Calm confident tone — no yelling or panic.

CRITICAL: EXACTLY 25-30 words of dialogue total in this video. Count every word inside "quotes".
If you write more than 30 words of dialogue, DELETE lines. This is a 5-second video — very little dialogue fits.
At the end of your output, write: [DIALOGUE WORD COUNT: XX]

---

YOUR HALF OF THE SCRIPT ({word_count} words — use ALL of these as dialogue, nothing else):
{script}"""

# ── STEP 2: Video 2 (RESOLUTION — payoff) ──

SYSTEM_VIDEO2 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 2 of 2 (CONCLUSION + CTA).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 2 = CONCLUSION + CTA
══════════════════════
FINAL SECTION. Pick up EXACTLY where Video 1 stopped — ZERO repeated lines.
This video starts fresh from a neutral seated position.
Use the remaining ~50% of the script that Video 1 did NOT cover.
Deliver the conclusion, moral, or final insight from the script.
~30 words of dialogue MAX — must be approximately EQUAL to Video 1 in length. Total across both = 60 words max.

══════════════════════
CTA (MANDATORY — EXACT PATTERN!)
══════════════════════
The LAST thing he says is a simple CTA. Use ONLY one of these patterns:
- "I share more tips like this — link in bio."
- "More advice on my page — link in bio."
- "Follow for more — link in bio."
NEVER invent creative CTAs. NEVER say "comment [word]". NEVER mention apps, products, or tools.
Just: he gives advice → link in bio. That's it. This counts toward the word limit.

══════════════════════
ENDING
══════════════════════
End with quiet finality. The LAST shot should be a CLOSE-UP with a nod after CTA.

══════════════════════
OPENING — VIDEO 2
══════════════════════
Start on THREE-QUARTER VIEW. The character is in a neutral seated position, calm and composed.
Video 1 ended on a close-up — so this three-quarter view creates a clear cut when the two are joined.
Do NOT reference the first part of the story — just deliver the conclusion."""

USER_VIDEO2 = """Generate Video 2 of 2 (CONCLUSION + CTA) from this script.
Pick up EXACTLY where Video 1 left off. Do NOT repeat ANY line from Video 1. Zero overlap.
Use EXACT remaining lines from the script as dialogue — do NOT paraphrase. End with CTA.
2-3 camera changes. Calm delivery. End with quiet finality and a nod.

CRITICAL: EXACTLY 25-30 words of dialogue total in this video — SAME amount as Video 1. Count every word inside "quotes".
CTA counts toward the word limit. If you write more than 30 words of dialogue, DELETE lines.
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
    half = word_count // 2

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
