import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a viral TikTok content strategist. Your job is to rewrite
TikTok scripts to maximize engagement, provocation, and watch time. Keep the core
information and topic identical, but transform the delivery. Write in the same language
as the original script."""

REWRITE_PROMPT = """Rewrite this TikTok script to be more provocative, attention-grabbing,
and viral. Requirements:
- Make the opening hook impossible to scroll past (first 3 seconds must create tension or shock)
- Add controversy where possible (challenge conventional wisdom)
- Use pattern interrupts (unexpected statements, rhetorical questions)
- Create FOMO or fear of missing out
- End with a cliffhanger or strong call-to-action
- Keep the same topic and key facts
- Match the TikTok speaking style (conversational, punchy, short sentences)
- LENGTH: HALF the original! Cut it DOWN to ~50% of the original word count. Remove filler, repetition, weak sentences. Keep ONLY the strongest lines. Every word must earn its place. If the original is 200 words, yours must be ~100

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
