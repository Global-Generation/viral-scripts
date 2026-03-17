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
All cameras are FIXED on tripods. COMPLETELY STATIC. Zero movement within any shot.
All transitions are HARD CUTS — instant switch from one static angle to another static angle.

Every transition = CUT. Describe which angle we CUT TO.
Say "CUT TO close-up" or "CUT TO side view" — NOT "camera pushes in" or "camera orbits."
NEVER use these words FOR THE CAMERA: orbit, dolly, drift, push-in, pull-out, track, pan, slide, creep, arc, zoom, push, pull, glide, sweep, follow, close in, move closer.
Each angle is a FROZEN STATIC FRAME — the CAMERA does not move within a shot. The CHARACTER can move freely (gestures, lean, nod, turn).

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
DIALOGUE: Use EXACT phrases from the original script. Do NOT paraphrase, rewrite, or invent new dialogue. Pick the strongest lines and quote them word-for-word.
DIALOGUE LIMIT: 30-50 words of dialogue PER VIDEO. 3-4 camera changes per video.
Text chunks between camera changes: 1-2 sentences MAX of directorial description. Keep scene directions SHORT — focus on dialogue, not narration. Do NOT over-describe body language, emotions, or atmosphere.
SPLITTING RULE (CRITICAL — MUST BE PROPORTIONAL):
1. Count ALL words in the script
2. Video 1 dialogue = first ~40-50% of the script's words. Video 2 dialogue = remaining ~50-60% (including conclusion + CTA)
3. Both videos MUST have similar word counts in dialogue. If Video 1 has 60 words, Video 2 must also have ~60 words
4. If the script has 10 lines, Video 1 gets lines 1-5, Video 2 gets lines 6-10. NOT 1-8 and 9-10!"""

# ── STEP 1: Video 1 (HOOK — problem, tension rising) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 2 (the HOOK + TENSION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = SETUP + BUILDING INTEREST
══════════════════════
First ~40-50% of the script ONLY. Stop at the MIDPOINT — not at 70%, not at 80%.
Character stays composed. Never frantic.
The conclusion, moral, and payoff belong in Video 2.
End mid-story on a COMPLETE SENTENCE. The viewer wants to hear what comes next.

══════════════════════
ENDING
══════════════════════
Video 1 ends on a COMPLETE SENTENCE. The thought is finished grammatically, but the topic is left open — viewer wants to hear the resolution.
The LAST shot of Video 1 must be a CLOSE-UP — this is the splice point where Video 2 will be joined.
MANDATORY: The video ends with a SHORT PAUSE (1-2 seconds of silence). Character finishes speaking, holds eye contact with camera, slight pause. This pause is the cliffhanger moment before Video 2.

"""

USER_VIDEO1 = """Generate Video 1 of 2 (SETUP + INTEREST) from this script.
Use ONLY the first ~40-50% of the script as dialogue. STOP at the midpoint — leave the rest for Video 2.
Do NOT paraphrase or invent new lines. Do NOT include the conclusion or payoff.
Video 2 must have roughly the SAME amount of dialogue as Video 1 — so do NOT use more than half the script here.
3-4 camera changes. Calm confident tone — no yelling or panic.

Output the directorial description directly. No labels, no headers.
30-50 words of dialogue in "quotes" — taken word-for-word from the script. Start with the opening shot description.

---

SCRIPT ({word_count} words total — use only the first ~{half_words} words):
{script}"""

# ── STEP 2: Video 2 (RESOLUTION — payoff) ──

SYSTEM_VIDEO2 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 2 of 2 (RESOLUTION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 2 = RESOLUTION
══════════════════════
SECOND HALF. The payoff. Pick up EXACTLY where Video 1 stopped — ZERO repeated lines.
This video starts fresh from a neutral seated position.
Settles into delivery — lean back, open hands, steady voice.
Use exact lines from the script as dialogue. Cover the lines that Video 1 did NOT use.

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
OPENING — VIDEO 2
══════════════════════
Start on SIDE VIEW. The character is in a neutral seated position, calm and composed.
Video 1 ended on a close-up — so this side view creates a clear cut when the two are joined.
Do NOT reference the first half of the story — just deliver the resolution."""

USER_VIDEO2 = """Generate Video 2 of 2 (RESOLUTION) from this script.
Pick up EXACTLY where Video 1 left off. Do NOT repeat ANY line from Video 1. Zero overlap.
Use EXACT lines from the script as dialogue — do NOT paraphrase. 30-50 words of dialogue (including CTA).
3-4 camera changes. Calm delivery. End with quiet finality.

Output the directorial description directly. No labels, no headers.
30-50 words of dialogue in "quotes" — taken word-for-word from the script, ending with a nod. Start with the opening shot description.

---

VIDEO 1 ALREADY GENERATED (DO NOT REPEAT ANY OF THIS):
{video1}

---

FULL SCRIPT:
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
    word_count = len(script_text.split())
    half_words = word_count // 2

    # Step 1: Generate Video 1 (Hook + Tension)
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(script=script_text, word_count=word_count, half_words=half_words)}]
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
        max_tokens=700,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(script=script_text, video1=video1_text)}]
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
