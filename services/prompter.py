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
~25-35 words of dialogue PER VIDEO (short!). Only 2-3 camera changes per video.
Text chunks between camera changes: 1 sentence each. Keep it TIGHT."""

# ── STEP 1: Video 1 (HOOK — attention grab) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 3 (the HOOK).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = HOOK
══════════════════════
This is the first third of the story. Attention grab.
Energy starts from zero and SPIKES immediately.
Opening line is provocative, unexpected, or shocking.
2-3 punchy sentences maximum. Fast, aggressive delivery.
End mid-thought — energy building, not resolved.

══════════════════════
ENDING (CRITICAL!)
══════════════════════
Video 1 ends MID-THOUGHT. Sentence NOT finished. Energy climbing.

At the VERY END of your output, add:
SPLICE STATE: [exact final camera framing, camera movement direction, body pose, lean, energy level, facial expression, gaze]"""

USER_VIDEO1 = """Generate Video 1 of 3 (HOOK — attention grab) from this script.
Use the FIRST THIRD of the script content. Condense to ~25-35 words of dialogue.
Only 2-3 camera changes. Keep it SHORT and punchy.

Output:

VIDEO 1:
[directorial description, ~25-35 words of dialogue in "quotes"]

SPLICE STATE: [final frame state]

---

SCRIPT:
{script}"""

# ── STEP 2: Video 2 (DEVELOPMENT — tension builds) ──

SYSTEM_VIDEO2 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 2 of 3 (DEVELOPMENT).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 2 = DEVELOPMENT
══════════════════════
This is the middle third. Tension and argument build.
Energy does NOT drop — continues from Video 1's peak.
First frame = EXACT same state as Video 1 ended.
Then energy keeps building: more gesticulation, faster tempo,
leaning forward, voice rising. The argument deepens.
End at MAXIMUM tension — the peak of the entire piece.

══════════════════════
STARTING STATE (CRITICAL!)
══════════════════════
You will receive a SPLICE STATE from Video 1.
Your Video 2 MUST START from EXACTLY that state.
EXPLICITLY describe the starting state in your first sentence.

══════════════════════
ENDING (CRITICAL!)
══════════════════════
Video 2 ends at PEAK ENERGY. Maximum tension. Mid-sentence.

At the VERY END of your output, add:
SPLICE STATE: [exact final camera framing, camera movement direction, body pose, lean, energy level, facial expression, gaze]"""

USER_VIDEO2 = """Generate Video 2 of 3 (DEVELOPMENT — tension builds) from this script.
Use the MIDDLE THIRD of the script content. Condense to ~25-35 words of dialogue.
Only 2-3 camera changes. Keep it SHORT.

Video 1 ended with this state — start EXACTLY here:
{splice_state}

Output:

VIDEO 2:
[directorial description, ~25-35 words of dialogue in "quotes"]

SPLICE STATE: [final frame state]

---

SCRIPT:
{script}"""

# ── STEP 3: Video 3 (RESOLUTION — payoff) ──

SYSTEM_VIDEO3 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 3 of 3 (RESOLUTION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 3 = RESOLUTION
══════════════════════
This is the final third. The payoff.
Energy does NOT drop at start — continues from Video 2's peak.
First frame = EXACT same state as Video 2 ended.
Then SMOOTH transition: exhale, lean back, tone shifts
from tension to calm authority/confidence.
Middle — key insight delivered with weight.
End — IMPACT: final line, close-up, direct gaze, nod, silence. PERIOD.

══════════════════════
STARTING STATE (CRITICAL!)
══════════════════════
You will receive a SPLICE STATE from Video 2.
Your Video 3 MUST START from EXACTLY that state.
EXPLICITLY describe the starting state in your first sentence."""

USER_VIDEO3 = """Generate Video 3 of 3 (RESOLUTION — payoff) from this script.
Use the FINAL THIRD of the script content. Condense to ~25-35 words of dialogue.
Only 2-3 camera changes. Keep it SHORT. End with finality.

Video 2 ended with this state — start EXACTLY here:
{splice_state}

Output:

VIDEO 3:
[directorial description, ~25-35 words of dialogue in "quotes", ending with impact]

---

SCRIPT:
{script}"""


def generate_video_prompt(script_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Generate Video 1 (Hook)
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(script=script_text)}]
    )
    video1_full = response1.content[0].text.strip()

    # Extract splice state 1
    if "SPLICE STATE:" in video1_full:
        parts = video1_full.split("SPLICE STATE:", 1)
        video1_text = parts[0].strip()
        splice1 = parts[1].strip()
    else:
        video1_text = video1_full
        splice1 = "Close-up, camera drifting right, leaning forward, high energy, intense gaze into camera, mid-sentence"
        logger.warning("No SPLICE STATE in Video 1, using default")

    # Step 2: Generate Video 2 (Development)
    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(script=script_text, splice_state=splice1)}]
    )
    video2_full = response2.content[0].text.strip()

    # Extract splice state 2
    if "SPLICE STATE:" in video2_full:
        parts = video2_full.split("SPLICE STATE:", 1)
        video2_text = parts[0].strip()
        splice2 = parts[1].strip()
    else:
        video2_text = video2_full
        splice2 = "Medium shot, camera orbiting left, body tense and forward, peak energy, jaw set, direct stare"
        logger.warning("No SPLICE STATE in Video 2, using default")

    # Step 3: Generate Video 3 (Resolution)
    response3 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_VIDEO3,
        messages=[{"role": "user", "content": USER_VIDEO3.format(script=script_text, splice_state=splice2)}]
    )
    video3_text = response3.content[0].text.strip()

    # Combine all three
    return f"{video1_text}\n\n{video2_text}\n\n{video3_text}"
