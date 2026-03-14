import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Shared rules included in both steps
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
Face fills the entire frame. Camera straight on, at eye level.
Background blurred or barely visible. Only face, neck, top of shoulders visible.
Used for emotional impacts, pauses, direct gaze into camera.

MEDIUM SHOT:
Upper body — from waist/table to head. Camera straight on.
Hand gesticulation visible, object in hands, body posture. Background readable.
Main working framing for conversation.

WIDE 3/4:
Camera pulled back and shifted to the side — lateral angle approximately 30-45°.
Entire setting visible: furniture, walls, decor + character in context.
Character occupies ~40% of frame. Used for lists, pauses, "exhale" moments.

TRANSITIONS — describe as live camera movement:
"Camera smoothly pushes in on the face" / "Camera pulls back, revealing the room, side 3/4 angle" / "Close-up again — face fills the frame" — each transition = physical movement, NOT an edit cut.

══════════════════════
STRUCTURE
══════════════════════
HOOK (opening) — medium shot, direct gaze, first line
DEVELOPMENT — alternating close-up ↔ wide 3/4 ↔ medium
TURN — energy shift, close-up → medium
IMPACT — close-up, main idea, pause, direct gaze
FINALE — medium or wide 3/4 (different each time)

══════════════════════
OUTPUT FORMAT
══════════════════════
Character, location, frame format, resolution — all taken from reference photo and generator settings. Do NOT duplicate in prompt text.
Format — continuous text as a directorial scene description.
No lists, no timecodes, no bullet points.
~40-50 words of dialogue. Text chunks between camera changes must be EQUAL length (1-2 sentences each)."""

# ── STEP 1: Generate Video 1 ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 (the PROBLEM half).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = PROBLEM
══════════════════════
Energy BUILDS from start to end.
Start — calm tone, minimal gestures, direct gaze.
Middle — voice strengthens, gesticulation appears, lean forward.
End — energy at peak, body tense, leaning forward.
Thought NOT CLOSED. Sentence hangs. Feeling: "and then what?"
Speech tempo accelerates toward the end.

══════════════════════
ENDING (CRITICAL!)
══════════════════════
Video 1 ends MID-THOUGHT — character is still speaking,
energy is high, body leaning forward, gaze into camera.
The sentence is NOT finished. It hangs in the air.

At the VERY END of your output, add a line starting with:
SPLICE STATE: [describe the exact final camera framing, body pose, lean direction, energy level, facial expression, gaze direction, and the emotion on the face]

This splice state will be passed to the Video 2 generator to ensure continuity."""

USER_VIDEO1 = """Generate Video 1 (problem half) from this script.
Use approximately the FIRST HALF of the script content. Condense to ~40-50 words of dialogue.

Output format:

VIDEO 1:
[continuous directorial description with dialogue in "quotes"]

SPLICE STATE: [exact description of final frame state]

---

ORIGINAL SCRIPT:
{script}"""

# ── STEP 2: Generate Video 2 using splice state from Video 1 ──

SYSTEM_VIDEO2 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 2 (the SOLUTION half).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 2 = SOLUTION
══════════════════════
Energy does NOT DROP at the start.
First 1-2 seconds — THE SAME high energy as Video 1's ending.
Character continues with same tension, same pose, same tone.
Then SMOOTH transition: exhale, leans back, tone lowers,
tempo slows. Energy changes quality — from tension to confidence.
Middle — calm enumeration, open palms.
End — IMPACT: main idea, close-up, direct gaze, nod, silence.
Feeling of a PERIOD. Everything said.

══════════════════════
STARTING STATE (CRITICAL!)
══════════════════════
You will receive a SPLICE STATE describing exactly how Video 1 ended:
camera framing, body pose, energy level, facial expression.

Your Video 2 MUST START from EXACTLY that state — same framing,
same pose, same energy, as if the camera never stopped.
The character CONTINUES speaking at the same tension level.
Only THEN does the energy begin to shift.

In your prompt, EXPLICITLY describe this starting state in the first sentence
so the video generator reproduces it exactly."""

USER_VIDEO2 = """Generate Video 2 (solution half) from this script.
Use approximately the SECOND HALF of the script content. Condense to ~40-50 words of dialogue.

Video 1 ended with this state — your Video 2 MUST START from exactly this:
{splice_state}

Output format:

VIDEO 2:
[continuous directorial description with dialogue in "quotes", starting from the splice state above]

---

ORIGINAL SCRIPT:
{script}"""


def generate_video_prompt(script_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Generate Video 1
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_VIDEO1,
        messages=[{
            "role": "user",
            "content": USER_VIDEO1.format(script=script_text)
        }]
    )
    video1_full = response1.content[0].text.strip()

    # Extract splice state from Video 1 output
    splice_state = ""
    if "SPLICE STATE:" in video1_full:
        parts = video1_full.split("SPLICE STATE:", 1)
        video1_text = parts[0].strip()
        splice_state = parts[1].strip()
    else:
        video1_text = video1_full
        splice_state = "Medium shot, leaning forward, tense, direct gaze into camera, high energy, mid-sentence"
        logger.warning("No SPLICE STATE found in Video 1 output, using default")

    # Step 2: Generate Video 2 using splice state
    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_VIDEO2,
        messages=[{
            "role": "user",
            "content": USER_VIDEO2.format(script=script_text, splice_state=splice_state)
        }]
    )
    video2_text = response2.content[0].text.strip()

    # Combine both
    return f"{video1_text}\n\n{video2_text}"
