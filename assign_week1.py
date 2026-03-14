"""One-time script: assign top 42 AI scripts to Boris/Thomas/Daniel for Week 1.
Takes the 42 highest viral_score scripts, period. No round-robin nonsense.
Run inside the container: python assign_week1.py
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/analyzer.db")

from database import SessionLocal
from models import Script, Video, Search

db = SessionLocal()

# Step 1: Clear all existing assignments
cleared = db.query(Script).filter(Script.assigned_to != "", Script.assigned_to.isnot(None)).all()
for s in cleared:
    s.assigned_to = ""
db.commit()
print(f"Cleared {len(cleared)} existing assignments")

# Step 2: Get ALL AI scripts ordered by viral_score desc — top 42
top_scripts = (
    db.query(Script)
    .join(Video)
    .join(Search, Video.search_id == Search.id)
    .filter(Search.category == "ai")
    .order_by(Script.viral_score.desc(), Script.created_at.desc())
    .limit(42)
    .all()
)

print(f"Top 42 AI scripts by viral_score:")
for i, s in enumerate(top_scripts):
    print(f"  {i+1}. #{s.id} score={s.viral_score} char={s.character_type}")

# Step 3: Assign round-robin: boris, thomas, daniel, boris, thomas, daniel...
names = ["boris", "thomas", "daniel"]
for i, script in enumerate(top_scripts):
    script.assigned_to = names[i % 3]

db.commit()

# Summary
for name in names:
    person_scripts = [s for s in top_scripts if s.assigned_to == name]
    scores = [s.viral_score for s in person_scripts]
    print(f"\n{name.upper()}: {len(person_scripts)} scripts")
    print(f"  Scores: {scores}")
    print(f"  Min={min(scores)}, Max={max(scores)}, Avg={sum(scores)/len(scores):.0f}")
    for s in person_scripts:
        print(f"    #{s.id} score={s.viral_score} char={s.character_type}")

db.close()
print("\nDone!")
