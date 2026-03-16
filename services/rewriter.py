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
- LENGTH: cut to ~40% of the original word count. Ruthlessly trim. If a sentence doesn't add new information, delete it

Original script:
{script}

Rewrite:"""


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
    return response.content[0].text.strip()
