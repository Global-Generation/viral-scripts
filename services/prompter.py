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
DIALOGUE LIMIT: 30-50 words of dialogue PER VIDEO. 2-3 camera changes per video. Do NOT cut on every line — group multiple dialogue lines into one shot.
Between camera changes: ONLY the dialogue in quotes. No descriptions of emotions, expressions, tone, posture, gaze, atmosphere, or body language. The ONLY allowed actions are: "He pauses.", "He nods.", "Silence." — nothing else. Example format:

JUMP CUT TO three-quarter view.

"Dialogue goes here."

JUMP CUT TO close-up.

"Next dialogue line."
SPLITTING RULE (CRITICAL — SEQUENTIAL FILL):
The script is split into 3 videos SEQUENTIALLY:
1. Video 1 = first ~30-50 words from the beginning of the script
2. Video 2 = next ~30-50 words, picking up EXACTLY where Video 1 stopped
3. Video 3 = whatever text remains (may be shorter than 30 words — that's OK)
Each video uses EXACT lines from the script in order. No skipping, no rearranging."""

# ── STEP 1: Video 1 (HOOK — problem, tension rising) ──

SYSTEM_VIDEO1 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 1 of 3 (the HOOK + SETUP).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 1 = HOOK + SETUP
══════════════════════
Use ONLY the first ~30-50 words of the script. Stop early — the rest goes to Videos 2 and 3.
Character stays composed. Never frantic.
The conclusion, moral, and payoff belong in later videos.
End mid-story on a COMPLETE SENTENCE. The viewer wants to hear what comes next.

══════════════════════
ENDING
══════════════════════
Video 1 ends on a COMPLETE SENTENCE. The thought is finished grammatically, but the topic is left open.
The LAST shot of Video 1 must be a CLOSE-UP — this is the splice point where Video 2 will be joined.
End with a brief beat — just a quick pause after the last line. No long silence.

"""

USER_VIDEO1 = """Generate Video 1 of 3 (HOOK + SETUP) from this script.
Use ONLY the first ~30-50 words of the script as dialogue. STOP early — leave the rest for Videos 2 and 3.
Do NOT paraphrase or invent new lines. Do NOT include the conclusion or payoff.
2-3 camera changes. Calm confident tone — no yelling or panic.

Output the directorial description directly. No labels, no headers.
30-50 words of dialogue in "quotes" — taken word-for-word from the script. Start with the opening shot description.

---

SCRIPT ({word_count} words total — use only the first ~{third_words} words):
{script}"""

# ── STEP 2: Video 2 (RESOLUTION — payoff) ──

SYSTEM_VIDEO2 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 2 of 3 (DEVELOPMENT).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 2 = DEVELOPMENT
══════════════════════
MIDDLE SECTION. Pick up EXACTLY where Video 1 stopped — ZERO repeated lines.
This video starts fresh from a neutral seated position.
Settles into delivery — lean back, open hands, steady voice.
Use exact lines from the script as dialogue. Use the next ~30-50 words that Video 1 did NOT cover.
Do NOT include the CTA — that belongs in Video 3.

══════════════════════
ENDING
══════════════════════
Video 2 ends on a COMPLETE SENTENCE. The topic is still open — viewer wants to hear the conclusion.
The LAST shot of Video 2 must be a CLOSE-UP — this is the splice point where Video 3 will be joined.
End with a brief beat — just a quick pause after the last line. No long silence.

══════════════════════
OPENING — VIDEO 2
══════════════════════
Start on THREE-QUARTER VIEW. The character is in a neutral seated position, calm and composed.
Video 1 ended on a close-up — so this three-quarter view creates a clear cut when the two are joined.
Do NOT reference the first part of the story — just continue delivering."""

USER_VIDEO2 = """Generate Video 2 of 3 (DEVELOPMENT) from this script.
Pick up EXACTLY where Video 1 left off. Do NOT repeat ANY line from Video 1. Zero overlap.
Use EXACT lines from the script as dialogue — do NOT paraphrase. 30-50 words of dialogue. NO CTA — that's in Video 3.
2-3 camera changes. Calm delivery. End mid-story — leave the conclusion for Video 3.

Output the directorial description directly. No labels, no headers.
Do NOT output any "CAMERA SETUP:" block — start directly with the opening shot angle and action.
30-50 words of dialogue in "quotes" — taken word-for-word from the script. Start with the opening shot description.

---

VIDEO 1 ALREADY GENERATED (DO NOT REPEAT ANY OF THIS):
{video1}

---

FULL SCRIPT:
{script}"""


# ── STEP 3: Video 3 (CONCLUSION — payoff + CTA) ──

SYSTEM_VIDEO3 = f"""You are a professional video director for vertical TikTok/Reels content.
You generate a SINGLE video prompt — Video 3 of 3 (CONCLUSION).

{SHARED_RULES}

══════════════════════
ENERGY — VIDEO 3 = CONCLUSION + CTA
══════════════════════
FINAL SECTION. Pick up EXACTLY where Video 2 stopped — ZERO repeated lines from Video 1 or Video 2.
This video starts fresh from a neutral seated position.
Use whatever script text remains. This may be shorter than 30 words — that's OK.
Deliver the conclusion, moral, or final insight from the script.

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
OPENING — VIDEO 3
══════════════════════
Start on THREE-QUARTER VIEW. The character is in a neutral seated position, calm and composed.
Video 2 ended on a close-up — so this three-quarter view creates a clear cut when the two are joined.
Do NOT reference earlier parts of the story — just deliver the conclusion."""

USER_VIDEO3 = """Generate Video 3 of 3 (CONCLUSION) from this script.
Pick up EXACTLY where Video 2 left off. Do NOT repeat ANY line from Video 1 or Video 2. Zero overlap.
Use EXACT remaining lines from the script as dialogue — do NOT paraphrase. End with CTA.
This video may be shorter — use whatever script text remains plus the CTA.
2-3 camera changes. Calm delivery. End with quiet finality.

Output the directorial description directly. No labels, no headers.
Do NOT output any "CAMERA SETUP:" block — start directly with the opening shot angle and action.
Dialogue in "quotes" — taken word-for-word from the script, ending with a nod after CTA. Start with the opening shot description.

---

VIDEO 1 ALREADY GENERATED (DO NOT REPEAT):
{video1}

---

VIDEO 2 ALREADY GENERATED (DO NOT REPEAT):
{video2}

---

FULL SCRIPT:
{script}"""


CAMERA_HEADER = """CAMERA SETUP:
Three angles — close-up (front), medium shot (front), three-quarter view (30-45° angle, NOT side profile).
All cameras are FIXED on tripods. COMPLETELY STATIC — zero camera movement.
All transitions are INSTANT JUMP CUTS. No smooth transitions, no panning, no zooming, no tracking.
Each shot is a frozen static frame from a different fixed camera angle.
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


def _strip_label(text: str, video_num: int) -> str:
    """Strip 'VIDEO N:' label and CAMERA SETUP block if AI accidentally adds them."""
    for prefix in (f"VIDEO {video_num}:", f"VIDEO {video_num} —", f"VIDEO {video_num}:"):
        if text.upper().startswith(prefix.upper()):
            text = text[len(prefix):].strip()
            break
    if "SPLICE STATE:" in text:
        text = text.split("SPLICE STATE:", 1)[0].strip()
    # Strip CAMERA SETUP block if AI outputs it despite instructions
    if text.startswith("CAMERA SETUP:"):
        lines = text.split("\n")
        # Find end of camera setup block (first empty line or line starting with a shot description)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if i > 0 and (stripped == "" and i > 3):
                # Skip past empty line after camera setup
                text = "\n".join(lines[i+1:]).strip()
                break
            if i > 0 and any(stripped.lower().startswith(a) for a in ["three-quarter", "medium shot", "close-up", "he "]):
                text = "\n".join(lines[i:]).strip()
                break
    return text


def generate_video_prompt(script_text: str) -> dict:
    """Return {"video1": ..., "video2": ..., "video3": ...} — each is a standalone filming prompt."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    word_count = len(script_text.split())
    third_words = word_count // 3

    # Step 1: Generate Video 1 (Hook + Setup)
    response1 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO1,
        messages=[{"role": "user", "content": USER_VIDEO1.format(script=script_text, word_count=word_count, third_words=third_words)}]
    )
    video1_text = _strip_label(response1.content[0].text.strip(), 1)

    # Step 2: Generate Video 2 (Development)
    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO2,
        messages=[{"role": "user", "content": USER_VIDEO2.format(script=script_text, video1=video1_text)}]
    )
    video2_text = _strip_label(response2.content[0].text.strip(), 2)

    # Step 3: Generate Video 3 (Conclusion + CTA)
    response3 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=SYSTEM_VIDEO3,
        messages=[{"role": "user", "content": USER_VIDEO3.format(script=script_text, video1=video1_text, video2=video2_text)}]
    )
    video3_text = _strip_label(response3.content[0].text.strip(), 3)

    _log_usage("prompt")
    _log_usage("prompt")
    _log_usage("prompt")  # three Claude calls per generation
    return {
        "video1": f"{CAMERA_HEADER}\n{video1_text}",
        "video2": video2_text,
        "video3": video3_text,
    }
