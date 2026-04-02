"""
Batch rewrite long scripts (>80 words) and delete empty ones.
Runs against a local DB copy, then generates SQL for production.

Usage: python3 batch_rewrite_long.py /tmp/viral_audit.db
"""
import sqlite3
import sys
import time
import os

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__) or '.')
from services.rewriter import rewrite_provocative


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/viral_audit.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Find unpublished scripts that are empty or >80 words
    c.execute("""
        SELECT s.id, s.assigned_to, s.modified_text, s.original_text
        FROM scripts s
        WHERE s.published_tiktok IS NULL
        ORDER BY s.id
    """)

    empty_ids = []
    long_scripts = []

    for row in c.fetchall():
        text = row['modified_text'] or row['original_text'] or ''
        wc = len(text.split()) if text.strip() else 0

        if not text.strip():
            empty_ids.append(row['id'])
        elif wc > 80:
            long_scripts.append({
                'id': row['id'],
                'text': text,
                'creator': row['assigned_to'] or 'unassigned',
                'word_count': wc,
            })

    print(f"Empty (will delete): {len(empty_ids)} — IDs: {empty_ids}")
    print(f"Long (will rewrite): {len(long_scripts)}")
    print()

    # 1. Delete empty scripts
    if empty_ids:
        placeholders = ','.join('?' * len(empty_ids))
        c.execute(f"DELETE FROM scripts WHERE id IN ({placeholders})", empty_ids)
        conn.commit()
        print(f"Deleted {len(empty_ids)} empty scripts.")

    # 2. Rewrite long scripts
    success = 0
    failed = 0
    rejected = 0

    for i, s in enumerate(long_scripts):
        sid = s['id']
        print(f"[{i+1}/{len(long_scripts)}] ID={sid} ({s['creator']}, {s['word_count']}w) ... ", end='', flush=True)

        try:
            rewritten = rewrite_provocative(s['text'])

            if rewritten.startswith("REJECTED"):
                print(f"REJECTED — deleting")
                c.execute("DELETE FROM scripts WHERE id = ?", (sid,))
                conn.commit()
                rejected += 1
                continue

            new_wc = len(rewritten.split())
            c.execute("UPDATE scripts SET modified_text = ? WHERE id = ?", (rewritten, sid))
            conn.commit()
            print(f"OK → {new_wc}w")
            success += 1

        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

        # Rate limit: ~1 req/sec
        if i < len(long_scripts) - 1:
            time.sleep(0.5)

    print()
    print(f"=== DONE ===")
    print(f"Deleted empty:  {len(empty_ids)}")
    print(f"Rewritten:      {success}")
    print(f"Rejected:       {rejected}")
    print(f"Failed:         {failed}")
    print(f"Total processed: {len(empty_ids) + success + rejected + failed}")

    conn.close()


if __name__ == "__main__":
    main()
