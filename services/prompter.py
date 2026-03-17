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
- Natural gesticulation: object in hands, fingers, palms, lean
- Face ALWAYS in frame
- No B-roll. No numbers/text on screen. No location changes

GESTICULATION BY EMOTION:
- Authority → finger/object toward camera, palm on table
- Sarcasm → counts on fingers, raises eyebrow
- Empathy → open palms, lean forward
- Impact → pause, direct gaze, nod

══════════════════════
CAMERA
══════════════════════
Three framing types. Alternate STRICTLY. Same framing twice in a row = FORBIDDEN.

CLOSE-UP:
Face fills the entire frame. Camera at eye level.
Background blurred or barely visible. Only face, neck, top of shoulders visible.

MEDIUM SHOT:
Upper body — from waist/table to head.
Hand gesticulation visible, object in hands, body posture. Background readable.

SIDE VIEW:
Camera shifted to the side — lateral angle approximately 30-45°.
Entire setting visible: furniture, walls, decor + character in context.
Character occupies ~40% of frame.

══════════════════════
CAMERA CUTS (CRITICAL — NO SMOOTH MOVEMENTS!)
══════════════════════
Three angles — close-up (front), medium shot (front), side view (30-45° offset).
All cameras are FIXED on tripods. The camera NEVER moves, orbits, tracks, drifts, or pushes in.
All transitions are HARD CUTS — instant switch from one angle to another.

Every transition = CUT. Describe which angle we CUT TO.
Say "CUT TO close-up" or "CUT TO side view" — NOT "camera pushes in" or "camera orbits."
NEVER use words: orbit, dolly, drift, push-in, pull-out, track, pan, slide, creep, arc.

══════════════════════
HOOK — FIRST 2 SECONDS
══════════════════════
The opening should feel natural and confident, NOT screaming or panicking.
Options (vary between scripts):
- Start on close-up, then CUT TO side view
- Start on side view, then CUT TO close-up
- Start on medium shot, mid-gesture, then CUT TO side view
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
DIALOGUE LIMIT: 25-35 words of dialogue PER VIDEO. This is a HARD LIMIT — count your words. If you exceed 35 words of dialogue in quotes, you have FAILED. 3-4 camera changes per video.
Text chunks between camera changes: 2-3 sentences each."""

# ── STEP 1: Video 1 (HOOK — problem, tension rising) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 2 (the HOOK + TENSION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = SETUP + BUILDING INTEREST
══════════════════════
FIRST HALF of the story. Confident opening, energy builds gradually.
Character stays composed. Never frantic. Keep dialogue MINIMAL — let visuals carry the scene.
End on a COMPLETE SENTENCE that creates intrigue. The sentence is finished, but the IDEA leaves the viewer wanting more.

══════════════════════
ENDING
══════════════════════
Video 1 ends on a COMPLETE SENTENCE. The thought is finished grammatically, but the topic is left open — viewer wants to hear the resolution. Energy is elevated but controlled.
The LAST shot of Video 1 must be a CLOSE-UP — this is the splice point where Video 2 will be joined.

"""

USER_VIDEO1 = """Generate Video 1 of 2 (SETUP + INTEREST) from this script.
Take the CORE IDEA from the first half of the script. Distill to 25-35 words of dialogue — do NOT try to cover everything.
3-4 camera changes. Calm confident tone — no yelling or panic.

Output the directorial description directly. No labels, no headers.
25-35 words of dialogue in "quotes". Start with the opening shot description.

---

SCRIPT:
{script}"""

# ── STEP 2: Video 2 (RESOLUTION — payoff) ──

SYSTEM_VIDEO2 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 2 of 2 (RESOLUTION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 2 = RESOLUTION
══════════════════════
SECOND HALF. The payoff. This video is SELF-CONTAINED — it starts fresh from a neutral seated position.
Settles into delivery — lean back, open hands, steady voice.
One key insight, then close. Direct gaze, slight nod. Done.
Keep dialogue MINIMAL — most of the scene is body language and camera work.

══════════════════════
CTA (MANDATORY — EXACT PATTERN!)
══════════════════════
The LAST thing he says is a simple CTA. Use ONLY one of these patterns:
- "I share more tips like this — link in bio."
- "More advice on my page — link in bio."
- "Follow for more — link in bio."
NEVER invent creative CTAs. NEVER say "comment [word]". NEVER mention apps, products, or tools.
Just: he gives advice → link in bio. That's it. This counts toward the 30-word limit.

══════════════════════
OPENING — VIDEO 2
══════════════════════
Start on SIDE VIEW. The character is in a neutral seated position, calm and composed.
Video 1 ended on a close-up — so this side view creates a clear cut when the two are joined.
Do NOT reference the first half of the story — just deliver the resolution."""

USER_VIDEO2 = """Generate Video 2 of 2 (RESOLUTION) from this script.
Take the CORE IDEA from the second half of the script. Distill to 25-35 words of dialogue (including CTA) — do NOT try to cover everything.
3-4 camera changes. Calm delivery. End with quiet finality.

Output the directorial description directly. No labels, no headers.
25-35 words of dialogue in "quotes", ending with a nod. Start with the opening shot description.

---

SCRIPT:
{script}"""


CAMERA_HEADER = """CAMERA SETUP:
Three angles — close-up (front), medium shot (front), side view (30-45° offset).
All cameras are FIXED on tripods. All transitions are HARD CUTS.
"""


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


def generate_video_prompt(script_text: str) -> dict:
    """Return {"video1": ..., "video2": ...} — each is a standalone filming prompt."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Generate Video 1 (Hook + Tension)
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(script=script_text)}]
    )
    video1_full = response1.content[0].text.strip()

    # Strip any accidental SPLICE STATE the model may still output
    if "SPLICE STATE:" in video1_full:
        video1_text = video1_full.split("SPLICE STATE:", 1)[0].strip()
    else:
        video1_text = video1_full

    # Strip "VIDEO 1:" label if present
    for prefix in ("VIDEO 1:", "VIDEO 1 —", "VIDEO 1:"):
        if video1_text.upper().startswith(prefix.upper()):
            video1_text = video1_text[len(prefix):].strip()
            break

    # Step 2: Generate Video 2 (Resolution)
    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(script=script_text)}]
    )
    video2_text = response2.content[0].text.strip()

    # Strip "VIDEO 2:" label if present
    for prefix in ("VIDEO 2:", "VIDEO 2 —", "VIDEO 2:"):
        if video2_text.upper().startswith(prefix.upper()):
            video2_text = video2_text[len(prefix):].strip()
            break

    _log_usage("prompt")
    _log_usage("prompt")  # two Claude calls per generation
    return {
        "video1": f"{CAMERA_HEADER}\n{video1_text}",
        "video2": f"{CAMERA_HEADER}\n{video2_text}",
    }
