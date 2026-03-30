import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a TikTok content strategist. Your job is to rewrite
TikTok scripts to be cleaner, tighter, and more watchable. Keep the core
information identical but improve the delivery. Write in the same language
as the original script."""

REWRITE_PROMPT = """Rewrite this TikTok script. Requirements:
- Clean opening hook — curiosity, not hype
- Calm confidence — the speaker states facts, not emotions. No exclamation marks unless truly needed
- NO emotional amplifiers: remove "literally", "insane", "crazy", "mind-blowing", "game-changer", "wake up", "you NEED to"
- NO fake urgency: remove "right now", "before it's too late", "most people don't know"
- Tone: dry, matter-of-fact, slightly witty. Think podcast host, not hype beast
- Short sentences. No fluff. Say it once
- Keep the same topic and key facts

LENGTH RULE — TARGET: 50-56 words TOTAL. This is a HARD LIMIT.
- CUT ruthlessly. One core point. No repetition. No examples unless essential.
- If the original is long: keep only the sharpest angle and strongest line.
- If the original is short: keep the key insight and develop it into 50-56 words.
- Every sentence must be COMPLETE. Never end mid-thought or mid-sentence.
- Count your words. If outside 50-56, adjust until you hit the range.

FORBIDDEN TOPICS — REJECT any script about:
- Suicide, self-harm, death, harm to minors
- AI causing psychological harm to children/teenagers
- Violence, abuse, criminal activity
- Tragic real-life incidents involving AI
If the original script contains these topics, respond with ONLY: "REJECTED: forbidden topic"

- OUTPUT: DIALOGUE ONLY. Plain spoken text, nothing else. No camera directions, no "MEDIUM SHOT", no "CLOSE-UP", no "JUMP CUT", no "THREE-QUARTER VIEW", no stage directions, no action descriptions, no headers, no labels, no markdown, no "Video 1" / "Video 2" splitting. Just the words the speaker says, as one continuous text
- CTA RULE: REMOVE any "Comment [word] for..." or "DM [word] for..." lines from the original. Replace with a simple ending like: "More on my page — link in bio." or just end naturally without a CTA. NEVER keep "Comment X", "DM me X", or any engagement-bait CTA

Original script:
{script}

Rewrite:"""


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


def rewrite_provocative(original_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": REWRITE_PROMPT.format(script=original_text)
        }]
    )
    _log_usage("rewrite")
    return response.content[0].text.strip()


BORIS_SYSTEM_PROMPT = """You are a TikTok content strategist specializing in provocative, debate-sparking content.
Your job is to rewrite scripts into bold, confrontational takes that make viewers want to argue in the comments.
Write in the same language as the original script."""

BORIS_REWRITE_PROMPT = """Rewrite this TikTok script in BORIS STYLE. Requirements:
- Opening: bold controversial statement or hot take — hit the viewer immediately
- Tone: "I don't care if you disagree" energy — calm but cutting. Think Joe Rogan meets Naval Ravikant
- State opinions as facts. Challenge conventional wisdom. Make the viewer pick a side
- NO emotional amplifiers: remove "literally", "insane", "crazy", "mind-blowing", "game-changer"
- NO fake urgency: remove "right now", "before it's too late", "most people don't know"
- NO hype. NO exclamation marks. Just raw, quiet confidence
- Short sentences. Punchy. Every word earns its place
- Keep the same topic and key facts but angle them provocatively

LENGTH RULE — TARGET: 50-56 words TOTAL. This is a HARD LIMIT.
- CUT ruthlessly. One core provocative point. No repetition.
- Every sentence must be COMPLETE. Never end mid-thought.
- Count your words. If outside 50-56, adjust until you hit the range.

FORBIDDEN TOPICS — REJECT any script about:
- Suicide, self-harm, death, harm to minors
- AI causing psychological harm to children/teenagers
- Violence, abuse, criminal activity
- Tragic real-life incidents involving AI
If the original script contains these topics, respond with ONLY: "REJECTED: forbidden topic"

- OUTPUT: DIALOGUE ONLY. Plain spoken text, nothing else. No camera directions, no stage directions, no labels, no markdown
- CTA RULE: REMOVE any "Comment X for..." or "DM me X for..." lines. Replace with "More on my page — link in bio." or end naturally

Original script:
{script}

Rewrite (Boris style — provocative, confrontational, debate-sparking):"""


def rewrite_provocative_boris(original_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=BORIS_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": BORIS_REWRITE_PROMPT.format(script=original_text)
        }]
    )
    _log_usage("rewrite_boris")
    return response.content[0].text.strip()
