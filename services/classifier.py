import anthropic
import logging
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You classify TikTok scripts into exactly one character type for video production.

The 4 character types:
- grandpa: "Wall Street Grandpa" — wise old investor with life experience. Best for: lessons learned the hard way, market wisdom, "back in my day" stories, calm authoritative advice, warnings about mistakes, long-term thinking.
- auntie: "Wall Street Auntie" — energetic, straight-talking finance woman. Best for: motivational money talk, bold claims, "listen up!", hustle culture, direct financial advice, sassy confidence.
- techguy: "IT Guy" — tech geek, programmer type. Best for: AI tools, ChatGPT tricks, coding, automation, technical how-tos, data and numbers, geeky humor, side hustles using technology.
- cartoon: "Cartoon Character" — for animation. Best for: absurd humor, memes, simple analogies, visual comedy, reactions, short punchy jokes, exaggerated scenarios, kid-friendly explanations.

Rules:
- Respond with ONLY the character type keyword: grandpa, auntie, techguy, or cartoon
- No explanation, no other text
- If the script is about AI/tech tools/ChatGPT → lean toward techguy
- If the script is motivational money/hustle talk → lean toward auntie
- If the script has wisdom/warnings/experience → lean toward grandpa
- If the script is funny/absurd/meme-like/very short → lean toward cartoon"""

CLASSIFY_PROMPT = """Classify this TikTok script:

{script}"""


def classify_script(text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=10,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(script=text[:500])}],
    )
    result = response.content[0].text.strip().lower()
    valid = {"grandpa", "auntie", "techguy", "cartoon"}
    if result not in valid:
        logger.warning(f"Unexpected classification: {result}, defaulting to cartoon")
        return "cartoon"
    return result
