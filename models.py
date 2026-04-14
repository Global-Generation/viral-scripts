from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Search(Base):
    __tablename__ = "searches"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, nullable=False)
    category = Column(String, default="")
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    videos = relationship("Video", back_populates="search", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("searches.id"), nullable=True)
    tiktok_url = Column(String, nullable=False)
    title = Column(String, default="")
    description = Column(Text, default="")
    score = Column(Float, default=0.0)
    status = Column(String, default="found")
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    search = relationship("Search", back_populates="videos")
    script = relationship("Script", back_populates="video", uselist=False,
                          cascade="all, delete-orphan")


class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, unique=True)
    original_text = Column(Text, default="")
    modified_text = Column(Text, default="")
    character_type = Column(String, default="")
    viral_score = Column(Integer, default=0)
    assigned_to = Column(String, default="")
    production_status = Column(String, default="")
    published_tiktok = Column(DateTime, nullable=True)
    published_youtube = Column(DateTime, nullable=True)
    published_instagram = Column(DateTime, nullable=True)
    video_prompt = Column(Text, default="")
    video1_prompt = Column(Text, default="")
    video2_prompt = Column(Text, default="")
    video3_prompt = Column(Text, default="")
    status = Column(String, default="extracted")
    # Final concatenated video
    final_video_path = Column(Text, default="")
    final_subtitled_path = Column(Text, default="")
    subtitle_status = Column(String, default="")
    subtitle_error = Column(Text, default="")
    # Raw uploaded videos (before trim/concat)
    raw_video1_path = Column(Text, default="")
    raw_video2_path = Column(Text, default="")
    # Publication metadata per platform
    pub_title_tiktok = Column(Text, default="")
    pub_desc_tiktok = Column(Text, default="")
    pub_tags_tiktok = Column(Text, default="")
    pub_title_instagram = Column(Text, default="")
    pub_desc_instagram = Column(Text, default="")
    pub_tags_instagram = Column(Text, default="")
    pub_title_youtube = Column(Text, default="")
    pub_desc_youtube = Column(Text, default="")
    pub_tags_youtube = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Channel (american / european)
    channel = Column(String, default="")
    # Final unified text (after pipeline + fact-checking + Claude unification)
    final_text = Column(Text, default="")
    # Fact-check report (JSON)
    fact_check_report = Column(Text, default="")

    video = relationship("Video", back_populates="script")
    pipeline_stages = relationship("PipelineStage", back_populates="script",
                                   cascade="all, delete-orphan",
                                   order_by="PipelineStage.id")


class PipelineStage(Base):
    """Stores each generation attempt for each stage of the script pipeline."""
    __tablename__ = "pipeline_stages"
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False, index=True)
    stage_name = Column(String, nullable=False)  # intro, part1, part2, part3, enrichment
    prompt_used = Column(Text, default="")
    result_text = Column(Text, default="")
    status = Column(String, default="pending")  # pending, generating, accepted, rejected
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)

    script = relationship("Script", back_populates="pipeline_stages")


class NariVideo(Base):
    __tablename__ = "nari_videos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    production_status = Column(String, default="")
    published_tiktok = Column(DateTime, nullable=True)
    published_youtube = Column(DateTime, nullable=True)
    published_instagram = Column(DateTime, nullable=True)
    pub_title_tiktok = Column(Text, default="")
    pub_desc_tiktok = Column(Text, default="")
    pub_tags_tiktok = Column(Text, default="")
    pub_title_instagram = Column(Text, default="")
    pub_desc_instagram = Column(Text, default="")
    pub_tags_instagram = Column(Text, default="")
    pub_title_youtube = Column(Text, default="")
    pub_desc_youtube = Column(Text, default="")
    pub_tags_youtube = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)


class AnnaVideo(Base):
    __tablename__ = "anna_videos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    production_status = Column(String, default="")
    published_tiktok = Column(DateTime, nullable=True)
    published_youtube = Column(DateTime, nullable=True)
    published_instagram = Column(DateTime, nullable=True)
    pub_title_tiktok = Column(Text, default="")
    pub_desc_tiktok = Column(Text, default="")
    pub_tags_tiktok = Column(Text, default="")
    pub_title_instagram = Column(Text, default="")
    pub_desc_instagram = Column(Text, default="")
    pub_tags_instagram = Column(Text, default="")
    pub_title_youtube = Column(Text, default="")
    pub_desc_youtube = Column(Text, default="")
    pub_tags_youtube = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)


class PresetQuery(Base):
    __tablename__ = "preset_queries"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    query = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)


class Avatar(Base):
    __tablename__ = "avatars"
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("avatars.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    prompt = Column(Text, default="")
    image_url = Column(Text, default="")
    image_request_id = Column(String, default="")
    character_type = Column(String, default="")
    variant_label = Column(String, default="")  # e.g. "outfit_1", "new_look_2"
    soul_id = Column(String, default="")  # Higgsfield Soul ID for face-locked generation
    soul_id_status = Column(String, default="")  # training, ready, failed
    created_at = Column(DateTime, default=utcnow)

    parent = relationship("Avatar", remote_side=[id], backref="variants")
    video_generations = relationship("VideoGeneration", back_populates="avatar")


class VideoGeneration(Base):
    __tablename__ = "video_generations"
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    avatar_id = Column(Integer, ForeignKey("avatars.id"), nullable=True)
    video_number = Column(Integer, default=1)
    model_id = Column(String, default="higgsfield-ai/dop/standard")
    prompt = Column(Text, default="")
    image_url = Column(Text, default="")
    video_url = Column(Text, default="")
    request_id = Column(String, default="")
    status = Column(String, default="queued")
    duration = Column(Integer, default=5)
    aspect_ratio = Column(String, default="9:16")
    camera_movement = Column(String, default="")
    sound_enabled = Column(Boolean, default=False)
    slow_motion = Column(Boolean, default=False)
    speed_ramp = Column(String, default="auto")
    variant_index = Column(Integer, default=0)
    selected = Column(Boolean, default=False)
    end_frame_url = Column(Text, default="")
    error_message = Column(Text, default="")
    subtitle_text = Column(Text, default="")
    subtitle_status = Column(String, default="")
    subtitled_video_path = Column(String, default="")
    subtitle_error = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    script = relationship("Script", backref="video_generations")
    avatar = relationship("Avatar", back_populates="video_generations")


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False)
    label = Column(String, default="")
    key_value = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class SystemPrompt(Base):
    __tablename__ = "system_prompts"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


def get_prompt(key: str, default: str) -> str:
    """Read system prompt from DB, fallback to hardcoded default."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        row = db.query(SystemPrompt).filter(SystemPrompt.key == key).first()
        db.close()
        if row and row.value:
            return row.value
    except Exception:
        pass
    return default


class TiktokStats(Base):
    __tablename__ = "tiktok_stats"
    id = Column(Integer, primary_key=True, index=True)
    creator = Column(String, nullable=False, index=True)
    stat_type = Column(String, nullable=False)  # "profile" or "videos"
    data = Column(Text, default="{}")  # JSON payload
    updated_at = Column(DateTime, default=utcnow)


class TiktokStatsLog(Base):
    __tablename__ = "tiktok_stats_log"
    id = Column(Integer, primary_key=True, index=True)
    creator = Column(String, nullable=False, index=True)
    followers = Column(Integer, default=0)
    hearts = Column(Integer, default=0)
    videos = Column(Integer, default=0)
    following = Column(Integer, default=0)
    logged_at = Column(DateTime, nullable=False, default=utcnow)


class ApiUsage(Base):
    __tablename__ = "api_usage"
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    platform = Column(String, nullable=False)
    model_id = Column(String, default="")
    request_type = Column(String, default="")
    request_id = Column(String, default="")
    status = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)


# ── AKB LOCAL TABLES (copy-paste from Mentorship-AKB) ────────────

class AkbClient(Base):
    __tablename__ = "akb_clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    mentor_name = Column(String, default="")
    responsible_name = Column(String, default="")
    status = Column(String, default="")
    tariff_type = Column(String, default="")
    tariff_price = Column(Float, nullable=True)
    currency = Column(String, default="RUB")
    payment_method = Column(String, default="")
    product_type = Column(String, default="")
    target_country = Column(String, default="")
    target_year = Column(Integer, nullable=True)
    telegram = Column(String, default="")
    age = Column(Integer, nullable=True)
    last_payment_date = Column(String, default="")
    agreement_status = Column(String, default="")
    is_akb = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)


class AkbMentor(Base):
    __tablename__ = "akb_mentors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    university = Column(String, default="")
    degree = Column(String, default="")
    major = Column(String, default="")
    graduation_year = Column(Integer, nullable=True)
    specializations = Column(Text, default="[]")   # JSON list
    countries = Column(Text, default="[]")          # JSON list
    universities_expertise = Column(Text, default="[]")  # JSON list
    students_helped = Column(Integer, default=0)
    success_rate = Column(Float, nullable=True)
    avg_scholarship_usd = Column(Integer, nullable=True)
    bio_short = Column(Text, default="")
    mentor_type = Column(String, default="")
    track_type = Column(String, default="")
    is_active = Column(Boolean, default=True)
    is_paused = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    email = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)


class AkbReview(Base):
    __tablename__ = "akb_reviews"
    id = Column(Integer, primary_key=True, index=True)
    university = Column(String, default="")
    student_name = Column(String, default="")
    student_country = Column(String, default="")
    rating = Column(Integer, nullable=True)
    text = Column(Text, default="")
    year = Column(Integer, nullable=True)
    is_verified = Column(Boolean, default=False)
    category = Column(String, default="")
    source = Column(String, default="")
    scholarship_amount = Column(Integer, nullable=True)
    offers_count = Column(Integer, nullable=True)
    mentor_name = Column(String, default="")
    program_level = Column(String, default="")
    created_at = Column(DateTime, default=utcnow)


class AkbSuccessStory(Base):
    __tablename__ = "akb_success_stories"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, default="")
    student_country = Column(String, default="")
    university = Column(String, default="")
    program = Column(String, default="")
    degree = Column(String, default="")
    admission_year = Column(Integer, nullable=True)
    admission_type = Column(String, default="")
    scholarship_usd = Column(Integer, nullable=True)
    scholarship_percent = Column(Float, nullable=True)
    financial_aid_total_usd = Column(Integer, nullable=True)
    story_short = Column(Text, default="")
    story_full = Column(Text, default="")
    quote = Column(Text, default="")
    highlights = Column(Text, default="[]")  # JSON list
    offers_received = Column(Integer, nullable=True)
    is_featured = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
