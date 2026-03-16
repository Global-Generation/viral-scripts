import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a viral TikTok content strategist. Your job is to rewrite
TikTok scripts to maximize engagement and watch time. Keep the core
information and topic identical, but make the delivery sharper and more compelling.
Write in the same language as the original script."""

REWRITE_PROMPT = """Rewrite this TikTok script to be more engaging, confident, and viral.
Requirements:
- Strong opening hook — first 3 seconds must create curiosity or tension
- Confident tone — speak like someone who KNOWS what they're talking about, not like someone yelling
- Challenge conventional wisdom where it fits naturally — don't force controversy
- Use rhetorical questions and pattern interrupts sparingly
- Keep the same topic and key facts
- Match the TikTok speaking style (conversational, punchy, short sentences)
- Tone: smart, direct, slightly provocative — NOT aggressive, NOT insulting, NOT clickbait-screaming
- Think "cool uncle who made it" not "angry influencer"
- LENGTH: HALF the original! Cut to ~50% of the original word count. Remove filler, repetition, weak sentences. Keep ONLY the strongest lines

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
