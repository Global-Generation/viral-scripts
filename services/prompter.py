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
HOOK — FIRST 2 SECONDS (CRITICAL!)
══════════════════════
The opening MUST grab attention immediately. Do NOT start with a calm medium shot.
Options (vary between scripts):
- Start TIGHT on close-up (Camera A), then CUT TO wide 3/4 (Camera B)
- Start on wide 3/4 (Camera B), then quick CUT TO close-up (Camera A)
- Start on medium (Camera A), mid-gesture, then CUT TO side angle (Camera B)
First CUT = fastest in the entire video. Rapid angle switch to create energy.

══════════════════════
OUTPUT FORMAT
══════════════════════
Character, location, frame format, resolution — all from reference photo. Do NOT describe.
Format — continuous text as a directorial scene description. No lists, no timecodes.
~40-50 words of dialogue PER VIDEO (short!). Only 3-4 camera changes per video.
Text chunks between camera changes: 1-2 sentences each. Keep it TIGHT."""

# ── STEP 1: Video 1 (HOOK — problem, tension rising) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 2 (the HOOK + TENSION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = HOOK + RISING TENSION
══════════════════════
This is the FIRST HALF of the story. Attention grab + tension building.
Energy starts from zero and SPIKES immediately with a provocative opening.
Then keeps building: more gesticulation, faster tempo, leaning forward.
The argument deepens and intensifies throughout.
End MID-THOUGHT at PEAK ENERGY — sentence NOT finished. Maximum tension.

══════════════════════
ENDING (CRITICAL!)
══════════════════════
Video 1 ends MID-THOUGHT. Sentence NOT finished. Energy at PEAK.

At the VERY END of your output, add:
SPLICE STATE: [exact final camera framing, body pose, lean, energy level, facial expression, gaze]"""

USER_VIDEO1 = """Generate Video 1 of 2 (HOOK + TENSION) from this script.
Use the FIRST HALF of the script content. Condense to ~40-50 words of dialogue.
Only 3-4 camera changes. Keep it SHORT and punchy.

Output:

VIDEO 1:
[directorial description, ~40-50 words of dialogue in "quotes"]

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
This is the SECOND HALF. The payoff.
Energy does NOT drop at start — continues from Video 1's peak.
First frame = EXACT same state as Video 1 ended.
Then SMOOTH transition: exhale, lean back, tone shifts
from tension to calm authority/confidence.
Middle — key insight delivered with weight.
End — IMPACT: final line, close-up, direct gaze, nod, silence. PERIOD.

══════════════════════
CTA / PRODUCT PLACEMENT (MANDATORY!)
══════════════════════
Near the END of Video 2, the character MUST naturally weave in a short CTA.
It should feel organic — part of the advice, NOT a hard sell.
The message: "your personal AI assistant is waiting — link in bio."
Variations (pick one, adapt to fit the script's tone):
- "...and if you need help with this — your AI assistant is right there, link in bio."
- "...I broke it all down for you with my AI assistant. Link in bio."
- "...want someone to walk you through it step by step? Link in bio."
- "...your assistant already has the answers. Check the link in bio."
Keep it to ONE short sentence. Weave it into the final thought — NOT as a separate block.

══════════════════════
STARTING STATE (CRITICAL!)
══════════════════════
You will receive a SPLICE STATE from Video 1.
Your Video 2 MUST START from EXACTLY that state.
EXPLICITLY describe the starting state in your first sentence."""

USER_VIDEO2 = """Generate Video 2 of 2 (RESOLUTION — payoff) from this script.
Use the SECOND HALF of the script content. Condense to ~40-50 words of dialogue.
Only 3-4 camera changes. Keep it SHORT. End with finality.

Video 1 ended with this state — start EXACTLY here:
{splice_state}

Output:

VIDEO 2:
[directorial description, ~40-50 words of dialogue in "quotes", ending with impact]

---

SCRIPT:
{script}"""


def generate_video_prompt(script_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Generate Video 1 (Hook + Tension)
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
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
        max_tokens=1024,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(script=script_text, splice_state=splice1)}]
    )
    video2_text = response2.content[0].text.strip()

    # Combine both
    return f"{video1_text}\n\n{video2_text}"
