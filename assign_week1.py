"""One-time script: assign top 42 AI scripts to Boris/Thomas/Daniel for Week 1.
Run inside the container: python assign_week1.py
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/analyzer.db")

from database import SessionLocal
from models import Script, Video, Search

db = SessionLocal()

# Get all AI scripts ordered by viral_score desc
ai_scripts = (
    db.query(Script)
    .join(Video)
    .join(Search, Video.search_id == Search.id)
    .filter(Search.category == "ai")
    .filter((Script.assigned_to == "") | (Script.assigned_to.is_(None)))
    .order_by(Script.viral_score.desc(), Script.created_at.desc())
    .all()
)

print(f"Found {len(ai_scripts)} unassigned AI scripts")

if len(ai_scripts) < 42:
    print(f"WARNING: Only {len(ai_scripts)} AI scripts available, need 42. Will assign what we have.")

# Round-robin by character type to spread variety across the 3 men
# Group by character type first
by_char = {}
for s in ai_scripts:
    ct = s.character_type or "unknown"
    by_char.setdefault(ct, []).append(s)

print("Character type distribution:")
for ct, scripts in by_char.items():
    print(f"  {ct}: {len(scripts)} scripts")

# Build interleaved list: pick from each character type in round-robin
interleaved = []
char_types = list(by_char.keys())
indices = {ct: 0 for ct in char_types}
while len(interleaved) < min(42, len(ai_scripts)):
    added = False
    for ct in char_types:
        if indices[ct] < len(by_char[ct]) and len(interleaved) < min(42, len(ai_scripts)):
            interleaved.append(by_char[ct][indices[ct]])
            indices[ct] += 1
            added = True
    if not added:
        break

# Assign: first 14 = boris, next 14 = thomas, last 14 = daniel
assignees = ["boris"] * 14 + ["thomas"] * 14 + ["daniel"] * 14
for i, script in enumerate(interleaved):
    if i >= len(assignees):
        break
    script.assigned_to = assignees[i]

db.commit()

# Summary
boris = [s for s in interleaved[:14]]
thomas = [s for s in interleaved[14:28]]
daniel = [s for s in interleaved[28:42]]

print(f"\nAssigned {min(len(interleaved), 42)} scripts:")
print(f"  Boris:  {len(boris)} scripts, chars: {[s.character_type for s in boris]}")
print(f"  Thomas: {len(thomas)} scripts, chars: {[s.character_type for s in thomas]}")
print(f"  Daniel: {len(daniel)} scripts, chars: {[s.character_type for s in daniel]}")

db.close()
print("Done!")
