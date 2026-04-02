"""Translate all not-done scripts to Russian."""
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

TRANSLATE_PROMPT = """Translate this TikTok script to Russian. Rules:
- Natural spoken Russian, short punchy sentences
- ALL numbers as words: "десять тысяч долларов" not "$10,000"
- Years stay as digits: "2026"
- Keep the same tone — calm, confident, factual
- OUTPUT: spoken text only, no labels, no markdown

Script:
{script}

Russian translation:"""


def main():
    with open('/tmp/not_done_scripts.json') as f:
        data = json.load(f)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    total = sum(len(v) for v in data.values())
    i = 0

    for speaker, scripts in data.items():
        for s in scripts:
            i += 1
            print(f"[{i}/{total}] {speaker} ID={s['id']} ... ", end='', flush=True)
            try:
                resp = client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=512,
                    messages=[{"role": "user", "content": TRANSLATE_PROMPT.format(script=s['text_en'])}]
                )
                ru = resp.content[0].text.strip()
                s['text_ru'] = ru
                print(f"OK → {len(ru.split())}w")
            except Exception as e:
                s['text_ru'] = ''
                print(f"ERROR: {e}")
            if i < total:
                time.sleep(0.5)

    with open('/tmp/not_done_translated.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nDone. {total} translated.")


if __name__ == "__main__":
    main()
