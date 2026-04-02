"""
Batch rewrite REWORK scripts for assigned creators.
Saves results to a JSON file for review before applying.

Usage: python3 batch_rewrite_rework.py /app/data/analyzer.db
"""
import sqlite3
import sys
import time
import os
import json
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__) or '.')
from services.rewriter import rewrite_provocative

FORBIDDEN_PHRASES = [
    "literally", "insane", "crazy", "mind-blowing", "mind blowing",
    "game-changer", "game changer", "wake up", "you need to",
    "right now", "before it's too late", "most people don't know",
    "as you can see", "check this", "look at this",
    "comment", "dm me", "link in the description",
    "game changing", "jaw-dropping", "jaw dropping",
    "believe it or not", "you won't believe",
]


def is_rework(text):
    if not text or not text.strip():
        return False
    wc = len(text.split())
    if wc < 20 or wc > 80:
        return False
    issues = []
    text_lower = text.lower()
    if wc < 30: issues.append("short")
    elif wc > 50: issues.append("long")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            issues.append("forbidden")
            break
    if re.search(r'!', text): issues.append("exclamation")
    if re.search(r'\$[\d,]+|\b\d{2,}\b', text): issues.append("digits")
    if re.search(r'\b(\d+)\s+(things?|steps?|ways?|tips?|reasons?|secrets?|hacks?|tricks?|mistakes?)\b', text, re.I):
        issues.append("listicle")
    stripped = text.strip()
    if stripped and stripped[-1] not in '.!?"': issues.append("no_punct")
    first_lower = stripped.split('.')[0].lower().strip() if stripped else ""
    for opener in ["so", "hey", "hi", "hello", "today", "in this video", "let me tell you"]:
        if first_lower.startswith(opener):
            issues.append("weak_hook")
            break
    return len(issues) > 0


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/analyzer.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get REWORK scripts for assigned creators only
    c.execute("""
        SELECT s.id, s.assigned_to, s.modified_text, s.original_text, sr.category
        FROM scripts s
        LEFT JOIN videos v ON s.video_id = v.id
        LEFT JOIN searches sr ON v.search_id = sr.id
        WHERE s.assigned_to IS NOT NULL
          AND s.assigned_to != ''
          AND s.assigned_to != 'unassigned'
        ORDER BY s.assigned_to, s.id
    """)

    rework_scripts = []
    for row in c.fetchall():
        text = row['modified_text'] or row['original_text'] or ''
        if is_rework(text):
            rework_scripts.append({
                'id': row['id'],
                'creator': row['assigned_to'],
                'category': row['category'] or '',
                'old_text': text,
                'old_wc': len(text.split()),
            })

    print(f"REWORK scripts to rewrite: {len(rework_scripts)}")
    by_cr = {}
    for s in rework_scripts:
        by_cr.setdefault(s['creator'], 0)
        by_cr[s['creator']] += 1
    for cr, cnt in sorted(by_cr.items()):
        print(f"  {cr}: {cnt}")
    print()

    results = []
    success = 0
    rejected = 0
    failed = 0

    for i, s in enumerate(rework_scripts):
        sid = s['id']
        print(f"[{i+1}/{len(rework_scripts)}] ID={sid} ({s['creator']}, {s['old_wc']}w) ... ", end='', flush=True)

        try:
            rewritten = rewrite_provocative(s['old_text'])

            if rewritten.startswith("REJECTED"):
                print(f"REJECTED")
                results.append({**s, 'new_text': None, 'new_wc': 0, 'status': 'rejected', 'reason': rewritten})
                rejected += 1
                continue

            new_wc = len(rewritten.split())
            print(f"OK → {new_wc}w")
            results.append({**s, 'new_text': rewritten, 'new_wc': new_wc, 'status': 'ok'})
            success += 1

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({**s, 'new_text': None, 'new_wc': 0, 'status': 'error', 'reason': str(e)})
            failed += 1

        if i < len(rework_scripts) - 1:
            time.sleep(0.5)

    conn.close()

    # Save results for review
    out_path = "/tmp/rework_rewrites.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n=== DONE ===")
    print(f"OK:       {success}")
    print(f"Rejected: {rejected}")
    print(f"Failed:   {failed}")
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
