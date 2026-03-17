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
- LENGTH: cut to ~30% of the original word count. Ruthlessly trim. If a sentence doesn't add new information, delete it. Target: 60-100 words TOTAL for the entire script. This will be split into two short videos — every word must earn its place
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
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": REWRITE_PROMPT.format(script=original_text)
        }]
    )
    _log_usage("rewrite")
    return response.content[0].text.strip()
