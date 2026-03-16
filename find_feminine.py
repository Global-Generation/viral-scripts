"""Find and unassign scripts with feminine content."""
import sys
from database import SessionLocal
from models import Script

db = SessionLocal()
scripts = db.query(Script).filter(
    Script.assigned_to.isnot(None),
    Script.assigned_to != "",
).all()

keywords = [
    "she ", "her ", "girl", "woman", "women", "female",
    "boyfriend", "husband", "make men", "men happy",
    "intimidate men", "dating", "relationship",
    "his attention", "queen", "ladies", "lady",
    "feminine", "wife", "married", "partner pays",
    "real man", "good man", "man does", "man who",
    "save me", "equal partner", "getting married",
    "feel secure", "i hide my", "toxic dating",
    "broke and single", "auntie", "sabrina", "jessica",
    "she's", "her success", "she doesn", "she can",
    "she want", "she need", "his woman", "his girl",
    "don't intimidate", "i show my ambitions",
    "my partner", "richer than", "build together",
    "personal guide",
]

found = []
for s in scripts:
    text = (s.original_text or "").lower()
    matches = [k for k in keywords if k in text]
    if matches:
        preview = (s.original_text or "")[:100].replace("\n", " ")
        found.append((s, matches, preview))

print(f"Found {len(found)} scripts with feminine/relationship content:")
for s, matches, preview in found:
    print(f"  #{s.id} [{s.assigned_to}] matches={matches[:5]}")
    print(f"    {preview}...")

if "--fix" in sys.argv:
    for s, matches, preview in found:
        s.assigned_to = ""
        print(f"  Unassigned #{s.id}")
    db.commit()
    print(f"\nDONE: unassigned {len(found)} scripts")
else:
    print(f"\nRun with --fix to unassign these {len(found)} scripts")

db.close()
