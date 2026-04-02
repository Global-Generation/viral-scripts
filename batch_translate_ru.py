"""
Translate rewritten scripts to Russian, numbers as words.
Reads from rework_rewrites.json, outputs rework_rewrites_ru.json.
"""
import json
import sys
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
- Natural spoken Russian, not literary. Short punchy sentences
- ALL numbers must be written as words: "десять тысяч долларов" not "$10,000", "тридцать процентов" not "30%"
- Years stay as digits: "2026"
- Keep the same tone — calm, confident, factual
- If the text contains meta-instructions like "45-50 words" or "rewrite" — ignore them and translate ONLY the actual script content
- If there is no actual script (only meta-instructions), respond with: "REJECTED: no script"
- OUTPUT: spoken text only, no labels, no markdown

Script:
{script}

Russian translation:"""


def translate(text):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": TRANSLATE_PROMPT.format(script=text)}]
    )
    return response.content[0].text.strip()


def main():
    with open('/tmp/rework_rewrites.json') as f:
        data = json.load(f)

    ok_items = [d for d in data if d['status'] == 'ok']
    print(f"Translating {len(ok_items)} scripts to Russian...")

    results = []
    success = 0
    rejected = 0
    failed = 0

    for i, d in enumerate(ok_items):
        sid = d['id']
        print(f"[{i+1}/{len(ok_items)}] ID={sid} ({d['creator']}) ... ", end='', flush=True)

        try:
            ru_text = translate(d['new_text'])

            if ru_text.startswith("REJECTED"):
                print("REJECTED")
                d['ru_text'] = None
                d['ru_status'] = 'rejected'
                rejected += 1
            else:
                ru_wc = len(ru_text.split())
                print(f"OK → {ru_wc}w")
                d['ru_text'] = ru_text
                d['ru_status'] = 'ok'
                success += 1

        except Exception as e:
            print(f"ERROR: {e}")
            d['ru_text'] = None
            d['ru_status'] = 'error'
            failed += 1

        results.append(d)

        if i < len(ok_items) - 1:
            time.sleep(0.5)

    # Also keep rejected items
    for d in data:
        if d['status'] == 'rejected':
            d['ru_text'] = None
            d['ru_status'] = 'rejected'
            results.append(d)

    with open('/tmp/rework_rewrites_ru.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n=== DONE ===")
    print(f"OK:       {success}")
    print(f"Rejected: {rejected}")
    print(f"Failed:   {failed}")


if __name__ == "__main__":
    main()
