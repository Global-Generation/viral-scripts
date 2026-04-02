"""Generate missing P1/P2 video prompts and apply all clickbait scripts to production DB."""
import json
import sqlite3
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

VIDEO_PROMPT_TEMPLATE = """Generate video prompts P1 and P2 for a TikTok script. The video shows ONLY a character sitting and talking to camera. No B-roll, no inserts, no text overlays.

Format exactly like this:
P1:
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays. ONLY the character sitting and talking. Nothing else on screen.

MEDIUM SHOT — The character sits composed, facing camera with calm authority.
"[First half of the script in quotes]"

- Slight head tilt as they state the key claim
- Minimal hand gesture on the emphasis word
- Direct eye contact throughout

P2:
NO B-roll. NO inserts of hands, pens, papers, objects. NO text overlays. ONLY the character sitting and talking. Nothing else on screen.

MEDIUM SHOT — The character sits facing camera with measured composure.
"[Second half of the script in quotes]"

- Slight lean forward for the punchline
- One deliberate pause before the final statement
- Composed expression, slight knowing look at end

Script to split into P1 and P2:
{script}

Generate P1 and P2:"""


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/analyzer.db"

    with open('/tmp/not_done_clickbait.json') as f:
        data = json.load(f)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Step 1: Generate missing P1/P2
    missing = []
    for speaker, scripts in data.items():
        for s in scripts:
            if not s.get('p1', '').strip() or not s.get('p2', '').strip():
                missing.append((speaker, s))

    print(f"Generating P1/P2 for {len(missing)} scripts...")
    for speaker, s in missing:
        sid = s['id']
        text = s.get('text_en', '')
        print(f"  ID={sid} ({speaker}) ... ", end='', flush=True)
        try:
            resp = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": VIDEO_PROMPT_TEMPLATE.format(script=text)}]
            )
            result = resp.content[0].text.strip()

            # Parse P1 and P2
            if 'P2:' in result:
                parts = result.split('P2:', 1)
                p1 = parts[0].replace('P1:', '').strip()
                p2 = parts[1].strip()
            else:
                # Split in half
                p1 = result[:len(result)//2].strip()
                p2 = result[len(result)//2:].strip()

            s['p1'] = p1
            s['p2'] = p2
            print(f"OK (P1={len(p1)}c, P2={len(p2)}c)")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.5)

    # Step 2: Apply clickbait EN texts + P1/P2 to production DB
    print(f"\nApplying to production DB...")
    updated = 0
    for speaker, scripts in data.items():
        for s in scripts:
            sid = int(s['id'])
            text_en = s.get('text_en', '')
            p1 = s.get('p1', '')
            p2 = s.get('p2', '')

            if text_en:
                c.execute("""UPDATE scripts SET modified_text = ?, video1_prompt = ?, video2_prompt = ?
                            WHERE id = ?""", (text_en, p1, p2, sid))
                updated += 1

    conn.commit()
    print(f"Updated {updated} scripts in DB")

    # Step 3: Save updated data
    with open('/tmp/not_done_final.json', 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Summary
    c.execute("""SELECT assigned_to, COUNT(*) FROM scripts
                WHERE assigned_to IS NOT NULL AND assigned_to != ''
                GROUP BY assigned_to ORDER BY assigned_to""")
    print("\nFinal counts:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # Check P1/P2 coverage
    c.execute("""SELECT COUNT(*) FROM scripts
                WHERE assigned_to IS NOT NULL AND assigned_to != ''
                AND (video1_prompt IS NULL OR video1_prompt = ''
                     OR video2_prompt IS NULL OR video2_prompt = '')""")
    print(f"\nStill missing P1/P2: {c.fetchone()[0]}")

    conn.close()


if __name__ == "__main__":
    main()
