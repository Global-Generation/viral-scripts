"""Apply rewritten scripts to production DB."""
import json
import sqlite3
import sys

def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/analyzer.db"

    with open('/tmp/rework_rewrites.json') as f:
        data = json.load(f)

    ok = [d for d in data if d['status'] == 'ok']
    rej = [d for d in data if d['status'] == 'rejected']

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Apply rewrites
    for d in ok:
        c.execute("UPDATE scripts SET modified_text = ? WHERE id = ?", (d['new_text'], d['id']))
    conn.commit()
    print(f"Applied {len(ok)} rewrites")

    # Delete rejected
    if rej:
        rej_ids = [d['id'] for d in rej]
        placeholders = ','.join('?' * len(rej_ids))
        c.execute(f"DELETE FROM scripts WHERE id IN ({placeholders})", rej_ids)
        conn.commit()
        print(f"Deleted {len(rej)} rejected scripts: {rej_ids}")

    # Summary per creator
    c.execute("""
        SELECT assigned_to, COUNT(*)
        FROM scripts
        WHERE assigned_to IS NOT NULL AND assigned_to != ''
        GROUP BY assigned_to
        ORDER BY assigned_to
    """)
    print("\nScripts per creator after update:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")

    c.execute("SELECT COUNT(*) FROM scripts WHERE assigned_to IS NULL OR assigned_to = ''")
    print(f"  unassigned: {c.fetchone()[0]}")

    c.execute("SELECT COUNT(*) FROM scripts")
    print(f"  TOTAL: {c.fetchone()[0]}")

    conn.close()


if __name__ == "__main__":
    main()
