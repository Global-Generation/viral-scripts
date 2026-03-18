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

LENGTH RULE — TARGET: 80-100 words TOTAL. This is a HARD LIMIT.
- If the original script is SHORT (under 80 words): EXPAND it. Add supporting details, examples, context, or a second angle on the same topic. Keep the same tone and topic — just flesh it out so there's enough material for two 40-50 word videos.
- If the original script is LONG (over 100 words): CUT to 80-100 words. Keep the strongest points. Remove repetition and filler.
- Count your words. If outside 80-100, adjust until you hit the range.

- OUTPUT: plain text only. No headers, no labels, no markdown, no "Video 1" / "Video 2" splitting. Just the rewritten script as one continuous text
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
