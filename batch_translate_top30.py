"""Translate top 30 unassigned scripts to Russian for review."""
import sqlite3
import json
import time
import sys
import os
import re
import anthropic

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

FORBIDDEN = ['literally','insane','crazy','mind-blowing','mind blowing','game-changer','game changer','wake up','you need to','right now',"before it's too late","most people don't know",'as you can see','check this','look at this','comment','dm me','link in the description','game changing','jaw-dropping','jaw dropping','believe it or not',"you won't believe"]

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
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/analyzer.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT s.id, s.modified_text, s.original_text, s.viral_score, sr.category,
               s.video1_prompt, s.video2_prompt
        FROM scripts s
        LEFT JOIN videos v ON s.video_id = v.id
        LEFT JOIN searches sr ON v.search_id = sr.id
        WHERE (s.assigned_to IS NULL OR s.assigned_to = '')
        ORDER BY s.viral_score DESC, s.id
    ''')

    candidates = []
    for row in c.fetchall():
        text = row['modified_text'] or row['original_text'] or ''
        wc = len(text.split()) if text.strip() else 0
        if not text.strip() or wc < 30 or wc > 60:
            continue
        text_lower = text.lower()
        issues = 0
        for phrase in FORBIDDEN:
            if phrase in text_lower: issues += 1
        if re.search(r'!', text): issues += 1
        if re.search(r'\$[\d,]+|\b\d{2,}\b', text): issues += 1
        stripped = text.strip()
        if stripped and stripped[-1] not in '.!?"': issues += 1
        if issues == 0:
            candidates.append({
                'id': row['id'],
                'text': text,
                'wc': wc,
                'score': row['viral_score'] or 0,
                'category': row['category'] or '',
                'p1': row['video1_prompt'] or '',
                'p2': row['video2_prompt'] or '',
            })

    candidates.sort(key=lambda x: -x['score'])
    top = candidates[:30]
    conn.close()

    print(f"Translating top {len(top)} scripts...")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = []

    for i, s in enumerate(top):
        print(f"[{i+1}/{len(top)}] ID={s['id']} (score={s['score']}) ... ", end='', flush=True)
        try:
            resp = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                messages=[{"role": "user", "content": TRANSLATE_PROMPT.format(script=s['text'])}]
            )
            ru = resp.content[0].text.strip()
            print(f"OK → {len(ru.split())}w")
            s['ru_text'] = ru
        except Exception as e:
            print(f"ERROR: {e}")
            s['ru_text'] = ''
        results.append(s)
        if i < len(top) - 1:
            time.sleep(0.5)

    with open('/tmp/top30_review.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to /tmp/top30_review.json")


if __name__ == "__main__":
    main()
