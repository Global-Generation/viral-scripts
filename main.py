import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db, SessionLocal
import models  # noqa: F401 — register all models with Base.metadata
from models import PresetQuery

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Viral Scripts")
app.mount("/static", StaticFiles(directory="static"), name="static")

from routers import pages, search, scripts, presets
app.include_router(pages.router)
app.include_router(search.router)
app.include_router(scripts.router)
app.include_router(presets.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    os.makedirs("./data", exist_ok=True)
    os.makedirs(os.getenv("DOWNLOADS_DIR", "./downloads"), exist_ok=True)
    init_db()
    _migrate_character_type()
    _seed_presets()


def _migrate_character_type():
    """Add new columns if they don't exist (for existing DBs)."""
    from sqlalchemy import text
    db = SessionLocal()
    for col, sql in [
        ("character_type", "ALTER TABLE scripts ADD COLUMN character_type VARCHAR DEFAULT ''"),
        ("viral_score", "ALTER TABLE scripts ADD COLUMN viral_score INTEGER DEFAULT 0"),
    ]:
        try:
            db.execute(text(f"SELECT {col} FROM scripts LIMIT 1"))
        except Exception:
            db.rollback()
            db.execute(text(sql))
            db.commit()
            logging.info(f"Migrated: added {col} column to scripts")
    db.close()


def _seed_presets():
    db = SessionLocal()
    try:
        if db.query(PresetQuery).count() > 0:
            return
        defaults = [
            PresetQuery(category="ai", query="AI tools that will replace your job", sort_order=0),
            PresetQuery(category="ai", query="ChatGPT secrets nobody tells you", sort_order=1),
            PresetQuery(category="ai", query="AI side hustle $10000 month", sort_order=2),
            PresetQuery(category="ai", query="AI automation business", sort_order=3),
            PresetQuery(category="ai", query="artificial intelligence future scary", sort_order=4),
            PresetQuery(category="finance", query="passive income 2026", sort_order=0),
            PresetQuery(category="finance", query="crypto millionaire strategy", sort_order=1),
            PresetQuery(category="finance", query="investing mistakes beginners", sort_order=2),
            PresetQuery(category="finance", query="financial freedom young", sort_order=3),
            PresetQuery(category="finance", query="money habits rich people", sort_order=4),
        ]
        db.add_all(defaults)
        db.commit()
        logging.info("Seeded default preset queries")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8070, reload=True)
