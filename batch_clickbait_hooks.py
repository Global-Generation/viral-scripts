"""Rewrite all not-done scripts with maximum clickbait hooks, same word count."""
import json
import time
import os
import anthropic

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

HOOK_PROMPT = """Rewrite this TikTok script. The ONLY change: make the opening hook MAXIMUM CLICKBAIT.

Rules:
- The first sentence must STOP the scroll. Use curiosity gaps, shocking contrasts, or bold claims
- Great hooks: "X just did Y and nobody's talking about it." / "This is why you're broke." / "I lost everything because of this one mistake." / "Delete this app right now." / "Nobody will tell you this."
- BAD hooks (too generic): "Most people think...", "Everyone says...", "Here's what happened..."
- Keep the REST of the script EXACTLY the same — only change the first 1-2 sentences
- CRITICAL: the total word count must be {wc} words or FEWER. Not one word more
- All numbers must be written as words (ten thousand, not 10,000). Years OK as digits
- No exclamation marks
- OUTPUT: the full rewritten script, spoken text only

Original ({wc} words):
{script}

Rewritten (max {wc} words, clickbait hook):"""

TRANSLATE_PROMPT = """Translate this TikTok script to Russian. Rules:
- Natural spoken Russian, short punchy sentences
- ALL numbers as words
- Years stay as digits: "2026"
- Same tone — calm, confident, factual
- OUTPUT: spoken text only

Script:
{script}

Russian translation:"""


def main():
    with open('/tmp/not_done_translated.json') as f:
        data = json.load(f)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    total = sum(len(v) for v in data.values())
    i = 0

    for speaker, scripts in data.items():
        for s in scripts:
            i += 1
            text = s.get('text_en', '')
            wc = len(text.split())
            print(f"[{i}/{total}] {speaker} ID={s['id']} ({wc}w) ... ", end='', flush=True)

            try:
                # Step 1: Clickbait hook rewrite
                resp = client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=512,
                    messages=[{"role": "user", "content": HOOK_PROMPT.format(script=text, wc=wc)}]
                )
                new_en = resp.content[0].text.strip()
                new_wc = len(new_en.split())

                # Reject if too long or looks like meta-text
                if new_wc > wc + 5 or new_en.startswith("REJECTED") or "I can't" in new_en:
                    print(f"SKIP (got {new_wc}w)")
                    continue

                s['text_en'] = new_en
                print(f"EN→{new_wc}w ", end='', flush=True)

                time.sleep(0.3)

                # Step 2: Translate to Russian
                resp2 = client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=512,
                    messages=[{"role": "user", "content": TRANSLATE_PROMPT.format(script=new_en)}]
                )
                new_ru = resp2.content[0].text.strip()
                s['text_ru'] = new_ru
                print(f"RU→{len(new_ru.split())}w")

            except Exception as e:
                print(f"ERROR: {e}")

            if i < total:
                time.sleep(0.3)

    with open('/tmp/not_done_clickbait.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nDone. {total} scripts processed.")


if __name__ == "__main__":
    main()
