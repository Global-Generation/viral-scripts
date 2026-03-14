import anthropic
import logging
import re
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a TikTok viral potential analyst. You score scripts from 0-100 based on objective virality metrics.

Scoring criteria (each 0-20 points):
1. HOOK STRENGTH (0-20): How strong is the opening? Does it create curiosity gap, shock, or tension in the first sentence? Would someone stop scrolling?
2. EMOTIONAL TRIGGER (0-20): Fear, greed, outrage, humor, surprise, FOMO — how much emotion does this script provoke?
3. SHAREABILITY (0-20): Would someone tag a friend or share this? Does it have "you need to see this" energy? Relatable content scores higher.
4. CONTROVERSY/DEBATE (0-20): Does it challenge conventional wisdom? Make a bold claim? Create "agree vs disagree" reactions in comments?
5. RETENTION (0-20): Does the script maintain attention throughout? Are there pattern interrupts, cliffhangers, or escalation? Would someone watch till the end?

Rules:
- Respond with ONLY a number from 0 to 100
- No explanation, no other text, just the number
- Be harsh — most scripts should score 30-60
- Only truly exceptional viral content gets 80+
- Generic/boring content gets below 30"""

SCORE_PROMPT = """Score this TikTok script's viral potential (0-100):

{script}"""


def score_viral_potential(text: str) -> int:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=5,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": SCORE_PROMPT.format(script=text[:500])}],
    )
    result = response.content[0].text.strip()
    match = re.search(r'\d+', result)
    if match:
        score = int(match.group())
        return min(max(score, 0), 100)
    logger.warning(f"Unexpected score response: {result}, defaulting to 50")
    return 50
