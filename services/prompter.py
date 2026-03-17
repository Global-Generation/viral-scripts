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
Camera can be slightly angled — adds life.

MEDIUM SHOT:
Upper body — from waist/table to head.
Hand gesticulation visible, object in hands, body posture. Background readable.

WIDE 3/4:
Camera pulled back and shifted to the side — lateral angle approximately 30-45°.
Entire setting visible: furniture, walls, decor + character in context.
Character occupies ~40% of frame.

══════════════════════
CAMERA CUTS (CRITICAL — NO SMOOTH MOVEMENTS!)
══════════════════════
Two cameras shoot simultaneously from different fixed positions.
The camera NEVER moves, orbits, tracks, drifts, or pushes in. Each camera is LOCKED on a tripod.
All transitions are HARD CUTS — instant switch from one angle to another.

CAMERA A: Front-facing, slightly off-center. Used for close-ups and medium shots.
CAMERA B: Side angle, ~30-45° offset. Used for wide 3/4 and alternate medium shots.

Every transition = CUT. Describe which camera/angle we CUT TO.
Say "CUT TO close-up from Camera A" — NOT "camera pushes in" or "camera orbits."
NEVER use words: orbit, dolly, drift, push-in, pull-out, track, pan, slide, creep, arc.

══════════════════════
HOOK — FIRST 2 SECONDS
══════════════════════
The opening should feel natural and confident, NOT screaming or panicking.
Options (vary between scripts):
- Start TIGHT on close-up (Camera A), then CUT TO wide 3/4 (Camera B)
- Start on wide 3/4 (Camera B), then CUT TO close-up (Camera A)
- Start on medium (Camera A), mid-gesture, then CUT TO side angle (Camera B)
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
DIALOGUE LIMIT: 20-30 words of dialogue PER VIDEO. This is a HARD LIMIT — count your words. If you exceed 30 words of dialogue in quotes, you have FAILED. Only 2-3 camera changes per video.
Text chunks between camera changes: 1-2 sentences each. Keep it TIGHT."""

# ── STEP 1: Video 1 (HOOK — problem, tension rising) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 2 (the HOOK + TENSION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = SETUP + BUILDING INTEREST
══════════════════════
FIRST HALF of the story. Confident opening, energy builds gradually.
Character stays composed. Never frantic. Keep dialogue MINIMAL — let visuals carry the scene.
End MID-THOUGHT — sentence NOT finished. Viewer wants to hear the rest.

══════════════════════
ENDING
══════════════════════
Video 1 ends MID-THOUGHT. Sentence NOT finished. Energy is elevated but controlled.

At the VERY END of your output, add:
SPLICE STATE: [exact final camera framing, body pose, lean, energy level, facial expression, gaze]"""

USER_VIDEO1 = """Generate Video 1 of 2 (SETUP + INTEREST) from this script.
Take the CORE IDEA from the first half of the script. Distill to strictly 20-30 words of dialogue — do NOT try to cover everything.
Only 2-3 camera changes. Keep it SHORT. Calm confident tone — no yelling or panic.

Output:

VIDEO 1:
[directorial description, 20-30 words MAX of dialogue in "quotes"]

SPLICE STATE: [final frame state]

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
SECOND HALF. The payoff. Continues from Video 1's state.
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
STARTING STATE (CRITICAL!)
══════════════════════
You will receive a SPLICE STATE from Video 1.
Your Video 2 MUST START from EXACTLY that state.
EXPLICITLY describe the starting state in your first sentence.
The FIRST 1 SECOND of Video 2 = SILENT BEAT. No dialogue. Character holds position from splice state — a breath, a look. THEN the first line begins. This pause is MANDATORY."""

USER_VIDEO2 = """Generate Video 2 of 2 (RESOLUTION) from this script.
Take the CORE IDEA from the second half of the script. Distill to strictly 20-30 words of dialogue (including CTA) — do NOT try to cover everything.
Only 2-3 camera changes. Be BRIEF — this is the shortest part. Calm delivery. End with quiet finality.

Video 1 ended with this state — start EXACTLY here:
{splice_state}

Output:

VIDEO 2:
[directorial description, 20-30 words MAX of dialogue in "quotes", ending with a nod]

---

SCRIPT:
{script}"""


def generate_video_prompt(script_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Generate Video 1 (Hook + Tension)
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(script=script_text)}]
    )
    video1_full = response1.content[0].text.strip()

    # Extract splice state
    if "SPLICE STATE:" in video1_full:
        parts = video1_full.split("SPLICE STATE:", 1)
        video1_text = parts[0].strip()
        splice1 = parts[1].strip()
    else:
        video1_text = video1_full
        splice1 = "Close-up from Camera A, leaning forward, high energy, intense gaze into camera, mid-sentence"
        logger.warning("No SPLICE STATE in Video 1, using default")

    # Step 2: Generate Video 2 (Resolution)
    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(script=script_text, splice_state=splice1)}]
    )
    video2_text = response2.content[0].text.strip()

    # Combine both
    return f"{video1_text}\n\n{video2_text}"
