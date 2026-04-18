"""Pipeline generator — stage-by-stage script generation replacing the old rewrite flow."""
import logging
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from models import get_prompt

logger = logging.getLogger(__name__)


class SafeFormatDict(dict):
    """Dict subclass that returns empty string for missing keys in str.format_map().
    Prevents KeyError when custom DB prompts lack {host_name} etc."""
    def __missing__(self, key):
        return ""

# Default prompts for each stage
DEFAULT_PROMPTS = {
    "intro": """You are a TikTok content strategist. Generate a powerful HOOK / INTRO for a viral short-form video.

CONTEXT: The original transcript is provided below. Your job is to create a 10-15 word opening hook that:
- Creates a curiosity gap — the viewer MUST watch to find out the answer
- Does NOT reveal the payoff
- Does NOT use fake hype: no "insane", "crazy", "mind-blowing", "you won't believe"
- Clean, calm, slightly provocative tone
- ONE sentence only
- Must relate directly to the topic

HOST/SPEAKER CONTEXT:
The speaker is {host_name}. Gender: {host_gender}.
{host_bio}
Write the hook in this person's voice and personality. Do NOT include a self-introduction — no "Hey I'm..." or name drops. Just match their tone.
If no speaker is specified, write in a neutral voice.

BRAND NAME PRONUNCIATION: Write compound brand names with spaces for TTS: "Open AI", "Chat G P T", "Mid Journey". Single real words stay: "Claude", "Gemini".
NUMBERS AS WORDS: "ten thousand dollars" not "$10,000". Years OK as digits.

Generate EXACTLY 3 different hook options, numbered 1-3. Each on its own line.
The user will pick one or ask for more options.

Original transcript:
{original_text}""",

    "part1": """You are a TikTok content strategist writing Part 1 of a 3-part viral script.

CONTEXT: This is the FIRST third of the script body (after the intro hook). It should:
- Establish the core premise or problem
- Create tension or surprise
- 15-20 words
- Flow naturally from the accepted intro hook
- Calm, factual, dry wit tone
- NO emotional amplifiers, NO fake urgency
- NO listicles or enumerations

HOST/SPEAKER: {host_name} ({host_gender}). Write in their voice and personality.

BRAND NAME PRONUNCIATION: Compound names spaced for TTS. Single words stay.
NUMBERS AS WORDS: Written out for TTS. Years OK as digits.
NO PHANTOM VISUALS: Person talking to camera only. No "as you can see" or screen references.

Accepted intro: {intro_text}
Original transcript:
{original_text}""",

    "part2": """You are a TikTok content strategist writing Part 2 of a 3-part viral script.

CONTEXT: This is the MIDDLE third of the script body. It should:
- Develop the idea from Part 1
- Add the key insight, data point, or twist
- 15-20 words
- Build on the momentum
- Same tone: calm, factual, dry wit

HOST/SPEAKER: {host_name} ({host_gender}). Maintain their voice.

BRAND NAME PRONUNCIATION: Compound names spaced for TTS.
NUMBERS AS WORDS: Written out. Years OK as digits.
NO PHANTOM VISUALS.

Accepted intro: {intro_text}
Accepted Part 1: {part1_text}
Original transcript:
{original_text}""",

    "part3": """You are a TikTok content strategist writing Part 3 of a 3-part viral script.

CONTEXT: This is the FINAL third. It should:
- Deliver the payoff or conclusion
- End with a subtle CTA or thought-provoking closer
- 10-15 words
- Land the message cleanly
- End with "Link in bio." as the very last sentence

HOST/SPEAKER: {host_name} ({host_gender}). Close in their voice.

BRAND NAME PRONUNCIATION: Compound names spaced for TTS.
NUMBERS AS WORDS: Written out. Years OK as digits.
NO PHANTOM VISUALS.

Accepted intro: {intro_text}
Accepted Part 1: {part1_text}
Accepted Part 2: {part2_text}
Original transcript:
{original_text}""",

    "enrichment": """You are a meticulous content editor. Take the 4 accepted parts of a TikTok script and produce a SINGLE UNIFIED script.

RULES:
- Combine intro + part1 + part2 + part3 into one cohesive flowing text
- Smooth transitions between parts — adjust wording for natural flow
- Keep total length 45-60 words
- Preserve the core message and tone from each part
- Fix any awkward joins
- Ensure every fact mentioned is accurate (use the fact-check report if provided)
- Output ONLY the final script text, no labels or headers

HOST/SPEAKER: {host_name} ({host_gender}).
{host_bio}
Ensure the unified script sounds like THIS person delivering it. Match their personality throughout.

Intro: {intro_text}
Part 1: {part1_text}
Part 2: {part2_text}
Part 3: {part3_text}
{fact_check_context}"""
}


def get_stage_prompt(stage_name: str) -> str:
    """Get the prompt for a pipeline stage (from DB or default)."""
    key = f"pipeline_{stage_name}"
    default = DEFAULT_PROMPTS.get(stage_name, "")
    return get_prompt(key, default)


def generate_stage(stage_name: str, original_text: str, context: dict = None) -> str:
    """Generate content for a pipeline stage using Claude.

    Args:
        stage_name: intro, part1, part2, part3, or enrichment
        original_text: The original transcript
        context: Dict with accepted texts from previous stages
            e.g. {"intro_text": "...", "part1_text": "...", ...}

    Returns:
        Generated text for this stage
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    context = context or {}
    prompt_template = get_stage_prompt(stage_name)

    # Format prompt with context
    format_vars = {
        "original_text": original_text or "",
        "intro_text": context.get("intro_text", ""),
        "part1_text": context.get("part1_text", ""),
        "part2_text": context.get("part2_text", ""),
        "part3_text": context.get("part3_text", ""),
        "fact_check_context": context.get("fact_check_context", ""),
        "host_name": context.get("host_name", ""),
        "host_bio": context.get("host_bio", ""),
        "host_gender": context.get("host_gender", ""),
    }
    user_prompt = prompt_template.format_map(SafeFormatDict(format_vars))

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text.strip()
