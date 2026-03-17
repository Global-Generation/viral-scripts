import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db, SessionLocal
import models  # noqa: F401 — register all models with Base.metadata
from models import PresetQuery, NariVideo, AnnaVideo, ApiKey

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Viral Scripts")
app.mount("/static", StaticFiles(directory="static"), name="static")

from routers import pages, search, scripts, presets, nari, anna, character, avatars, videos, settings
app.include_router(pages.router)
app.include_router(search.router)
app.include_router(scripts.router)
app.include_router(presets.router)
app.include_router(nari.router)
app.include_router(anna.router)
app.include_router(character.router)
app.include_router(avatars.router)
app.include_router(videos.router)
app.include_router(settings.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    os.makedirs("./data", exist_ok=True)
    os.makedirs(os.getenv("DOWNLOADS_DIR", "./downloads"), exist_ok=True)
    init_db()
    _migrate_character_type()
    _migrate_cinema_studio()
    _migrate_subtitle_fields()
    _migrate_avatar_variants()
    _migrate_video3_prompt()
    _seed_presets()
    _seed_nari()
    _seed_anna()
    _seed_api_keys()


def _migrate_character_type():
    """Add new columns if they don't exist (for existing DBs)."""
    from sqlalchemy import text
    db = SessionLocal()
    for col, sql in [
        ("character_type", "ALTER TABLE scripts ADD COLUMN character_type VARCHAR DEFAULT ''"),
        ("viral_score", "ALTER TABLE scripts ADD COLUMN viral_score INTEGER DEFAULT 0"),
        ("assigned_to", "ALTER TABLE scripts ADD COLUMN assigned_to VARCHAR DEFAULT ''"),
        ("production_status", "ALTER TABLE scripts ADD COLUMN production_status VARCHAR DEFAULT ''"),
        ("published_tiktok", "ALTER TABLE scripts ADD COLUMN published_tiktok DATETIME"),
        ("published_youtube", "ALTER TABLE scripts ADD COLUMN published_youtube DATETIME"),
        ("published_instagram", "ALTER TABLE scripts ADD COLUMN published_instagram DATETIME"),
        ("video_prompt", "ALTER TABLE scripts ADD COLUMN video_prompt TEXT DEFAULT ''"),
        ("video1_prompt", "ALTER TABLE scripts ADD COLUMN video1_prompt TEXT DEFAULT ''"),
        ("video2_prompt", "ALTER TABLE scripts ADD COLUMN video2_prompt TEXT DEFAULT ''"),
    ]:
        try:
            db.execute(text(f"SELECT {col} FROM scripts LIMIT 1"))
        except Exception:
            db.rollback()
            db.execute(text(sql))
            db.commit()
            logging.info(f"Migrated: added {col} column to scripts")
    # Fix any auntie → grandpa
    try:
        result = db.execute(text("UPDATE scripts SET character_type = 'grandpa' WHERE character_type = 'auntie'"))
        if result.rowcount > 0:
            db.commit()
            logging.info(f"Fixed {result.rowcount} scripts: auntie → grandpa")
    except Exception:
        db.rollback()
    db.close()


def _migrate_cinema_studio():
    """Create cinema studio tables if they don't exist."""
    from sqlalchemy import text, inspect
    db = SessionLocal()
    inspector = inspect(db.bind)
    existing = inspector.get_table_names()
    tables_needed = ["avatars", "video_generations", "api_keys", "api_usage"]
    if all(t in existing for t in tables_needed):
        db.close()
        return
    # Tables are created by init_db() via Base.metadata.create_all
    # Just log which new tables appeared
    for t in tables_needed:
        if t not in existing:
            logging.info(f"Cinema Studio migration: table '{t}' created")
    db.close()


def _migrate_subtitle_fields():
    """Add subtitle columns to video_generations if they don't exist."""
    from sqlalchemy import text
    db = SessionLocal()
    for col, sql in [
        ("subtitle_text", "ALTER TABLE video_generations ADD COLUMN subtitle_text TEXT DEFAULT ''"),
        ("subtitle_status", "ALTER TABLE video_generations ADD COLUMN subtitle_status VARCHAR DEFAULT ''"),
        ("subtitled_video_path", "ALTER TABLE video_generations ADD COLUMN subtitled_video_path VARCHAR DEFAULT ''"),
        ("subtitle_error", "ALTER TABLE video_generations ADD COLUMN subtitle_error TEXT DEFAULT ''"),
    ]:
        try:
            db.execute(text(f"SELECT {col} FROM video_generations LIMIT 1"))
        except Exception:
            db.rollback()
            db.execute(text(sql))
            db.commit()
            logging.info(f"Migrated: added {col} column to video_generations")
    db.close()


def _migrate_avatar_variants():
    """Add parent_id and variant_label columns to avatars if they don't exist."""
    from sqlalchemy import text
    db = SessionLocal()
    for col, sql in [
        ("parent_id", "ALTER TABLE avatars ADD COLUMN parent_id INTEGER REFERENCES avatars(id)"),
        ("variant_label", "ALTER TABLE avatars ADD COLUMN variant_label VARCHAR DEFAULT ''"),
    ]:
        try:
            db.execute(text(f"SELECT {col} FROM avatars LIMIT 1"))
        except Exception:
            db.rollback()
            db.execute(text(sql))
            db.commit()
            logging.info(f"Migrated: added {col} column to avatars")
    db.close()


def _migrate_video3_prompt():
    """Add video3_prompt column to scripts if it doesn't exist."""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        db.execute(text("SELECT video3_prompt FROM scripts LIMIT 1"))
    except Exception:
        db.rollback()
        db.execute(text("ALTER TABLE scripts ADD COLUMN video3_prompt TEXT DEFAULT ''"))
        db.commit()
        logging.info("Migrated: added video3_prompt column to scripts")
    db.close()


def _seed_api_keys():
    """Seed default API keys from .env if no keys exist yet."""
    from config import ANTHROPIC_API_KEY, TAVILY_API_KEY, HF_API_KEY, HF_API_SECRET
    db = SessionLocal()
    try:
        if db.query(ApiKey).count() > 0:
            return
        keys = []
        if HF_API_KEY and HF_API_SECRET:
            keys.append(ApiKey(
                platform="higgsfield",
                label="Default Higgsfield",
                key_value=f"{HF_API_KEY}:{HF_API_SECRET}",
                is_active=True,
            ))
        if ANTHROPIC_API_KEY:
            keys.append(ApiKey(
                platform="anthropic",
                label="Default Anthropic",
                key_value=ANTHROPIC_API_KEY,
                is_active=True,
            ))
        if TAVILY_API_KEY:
            keys.append(ApiKey(
                platform="tavily",
                label="Default Tavily",
                key_value=TAVILY_API_KEY,
                is_active=True,
            ))
        if keys:
            db.add_all(keys)
            db.commit()
            logging.info(f"Seeded {len(keys)} default API keys")
    finally:
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


def _seed_nari():
    db = SessionLocal()
    try:
        if db.query(NariVideo).count() > 0:
            return
        titles = [
            "Are You SAVING ENOUGH to Ensure Your Future Happiness?",
            "Break Free from Late Bills and Boost Your Credit Score",
            "Escaping DEBT in 2026: A Challenge No One Can Conquer",
            "Everyone advises you to save money, yet no one reveals the secrets to doing it.",
            "Everyone tells you to SAVE MONEY, but no one explains how",
            "How Unplanned Saving Can Sabotage Your Financial Success",
            "How Your Fear of Saving is Holding You Back Financially",
            "If you want a credit score ABOVE 700, this is what actually matters",
            "Many fear debt consolidation due to a lack of understanding",
            "Master THESE 3 ESSENTIAL Credit Score Basics",
            "Most adults MESS UP money because no one taught them this early.",
            "New credit card MISTAKE nobody warns you about: not using it at all.",
            "The biggest mistake people make when they get their first credit card",
            "The Critical Mistake Many Make When Tackling Debt: Trying to Do It All at Once",
            "The FASTEST Way to Optimize Your Credit Score Before Applying",
            "The shocking truth about WHY your credit cards get denied",
            "The SHOCKING truth about your credit report and mortgages",
            "The surprising secrets of building credit you never realized",
            "This mindset shift changed EVERYTHING about my debt journey",
            "Transform Your Finances: Discover the Truth About Your Money",
            "Unlock the secret to EXTRA MONEY with biweekly pay",
            "What is the fastest way to build credit from ZERO?",
            "Why SAVING MONEY feels impossible for most people",
            "Why Your Budget Fails and What You Can Do",
        ]
        db.add_all([NariVideo(title=t) for t in titles])
        db.commit()
        logging.info(f"Seeded {len(titles)} Nari videos")
    finally:
        db.close()


def _seed_anna():
    db = SessionLocal()
    try:
        if db.query(AnnaVideo).count() > 0:
            return
        titles = [
            "Break Free from Living Paycheck to Paycheck: Here's Where to Begin",
            "Discover the Exact Amount You Should Save from Each Biweekly Paycheck",
            "Escaping DEBT in 2026: A Daring Challenge!",
            "Everyone advises you to save money, but few reveal the secrets to doing it effectively",
            "Everyone advises you to SAVE MONEY, but no one reveals the secrets to doing it.",
            "I Conquered Over $80,000 in Student Loan Debt, but the Biggest Challenge Wasn't Financial",
            "I Paid Off $50K in My 20s: The Surprising Mistake Everyone Overlooks",
            "I understand your battle with overspending and sticking to a budget – you're not alone.",
            "I'm scared to let my savings dip to $1,000, but I know I must tackle my debt.",
            "Is Debt Consolidation the Right Move for You? Let's Simplify It!",
            "Many adults struggle with money because they never learned this crucial lesson early on",
            "Many fear debt consolidation due to a lack of understanding",
            "The ideal savings target for every age in the US: Are you on track? (1)",
            "The ideal savings target for every age in the US: Are you on track?",
            "Unlocking a Credit Score Above 700: The Key Factors That Truly Matter",
            "What You Need to Know if Your Credit Score is Below 700",
        ]
        db.add_all([AnnaVideo(title=t) for t in titles])
        db.commit()
        logging.info(f"Seeded {len(titles)} Anna videos")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8070, reload=True)
