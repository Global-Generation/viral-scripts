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

LENGTH RULE — TARGET: 45-50 words TOTAL. This is a HARD LIMIT.
- CUT ruthlessly. One core point. No repetition. No examples unless essential.
- If the original is long: keep only the sharpest angle and strongest line.
- If the original is short: keep the key insight and develop it into 45-50 words.
- Every sentence must be COMPLETE. Never end mid-thought or mid-sentence.
- Count your words. If outside 45-50, adjust until you hit the range.

NO LISTICLES OR ENUMERATIONS:
- NEVER use list format: "10 things", "5 tools", "here are 3 steps"
- NEVER count down or number items: "First... Second... Third...", "Number 10... Number 9..."
- NEVER enumerate tools, apps, or products one by one
- ONE core point, ONE angle. If the original is a listicle, pick the single most interesting item and build the entire script around just that one thing

BRAND NAME PRONUNCIATION RULE:
Write brand names with spaces so a text-to-speech model can pronounce them correctly:
- "Open AI" not "OpenAI"
- "Chat G P T" not "ChatGPT" — spell out G P T with spaces so TTS pronounces each letter
- "Mid Journey" not "Midjourney"
- "Notebook LM" not "NotebookLM"
- Single real words stay as-is: "Claude", "Gemini", "Grok", "Perplexity"
- Abbreviations that don't sound like words must be spaced: "G P T", "L L M" — but "AI" stays as "AI"
- When in doubt, add a space between logical word parts

NUMBERS AS WORDS RULE:
All numbers must be written as words for clear text-to-speech pronunciation.
- "ten thousand dollars" not "$10,000"
- "two thousand four hundred" not "$2,400"
- "thirty percent" not "30%"
- "one point five million" not "1.5 million"
- Round large numbers to simpler forms: "about twenty thousand" instead of "$19,847"
- Years are OK as digits: "2026" stays "2026"
- Avoid cramming too many numbers into one script. One or two stats maximum.

NO PHANTOM VISUAL REFERENCES:
The video is ONLY a person talking to camera. There are NO screen overlays, charts, screenshots, or B-roll.
- NEVER reference something "on screen": "as you can see", "look at this", "check out this chart"
- NEVER imply visual aids: "the blue line shows", "this graph proves", "here's a screenshot"
- NEVER reference swiping, scrolling, or UI elements
- If the original script references visuals, rewrite to convey the same information VERBALLY only

NO ADVERTISING OR PROMOTION:
- NEVER promote specific companies, banks, loan services, or products as recommendations
- NEVER include referral pitches, discount codes, or "I personally use this" endorsements
- Discussing a company as a NEWS TOPIC is fine. Recommending it as a product is NOT.

TOPIC RULE — AI, TECH, AND FINANCE ONLY:
- The script MUST be about artificial intelligence, technology, or finance/money
- REJECT any script that is off-topic: random stories, linguistics trivia, psychology facts, celebrity gossip, scams, dating
- If the original script is off-topic, respond with ONLY: "REJECTED: off-topic"

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

LENGTH RULE — TARGET: 45-50 words TOTAL. This is a HARD LIMIT.
- CUT ruthlessly. One core provocative point. No repetition.
- Every sentence must be COMPLETE. Never end mid-thought.
- Count your words. If outside 45-50, adjust until you hit the range.

NO LISTICLES OR ENUMERATIONS:
- NEVER use list format: "10 things", "5 tools", "here are 3 steps"
- NEVER count down or number items: "First... Second... Third...", "Number 10... Number 9..."
- NEVER enumerate tools, apps, or products one by one
- ONE core provocative point. If the original is a listicle, pick the single most controversial item and attack it

BRAND NAME PRONUNCIATION RULE:
Write brand names with spaces for text-to-speech clarity:
- "Open AI" not "OpenAI"
- "Chat G P T" not "ChatGPT" — spell out G P T with spaces so TTS pronounces each letter
- "Mid Journey" not "Midjourney"
- "Notebook LM" not "NotebookLM"
- Single real words stay as-is: "Claude", "Gemini", "Grok", "Perplexity"
- Abbreviations that don't sound like words must be spaced: "G P T", "L L M" — but "AI" stays as "AI"

NUMBERS AS WORDS RULE:
All numbers as words for TTS. Round large numbers.
- "ten thousand" not "$10,000". Years OK as digits.
- One or two stats maximum per script.

NO PHANTOM VISUAL REFERENCES:
The video is ONLY a person talking to camera. No screens, charts, or B-roll.
- NEVER reference something "on screen" or imply visual aids
- Convey all information VERBALLY

NO ADVERTISING OR PROMOTION:
- NEVER promote specific companies, banks, or products as recommendations
- Discussing a company as a NEWS TOPIC is fine. Recommending it is NOT.

TOPIC RULE — AI, TECH, AND FINANCE ONLY:
- REJECT off-topic scripts (random stories, linguistics, celebrity gossip, scams, dating)
- If off-topic, respond with ONLY: "REJECTED: off-topic"

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
