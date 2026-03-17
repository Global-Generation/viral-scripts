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
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    video = relationship("Video", back_populates="script")


class NariVideo(Base):
    __tablename__ = "nari_videos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    production_status = Column(String, default="")
    published_tiktok = Column(DateTime, nullable=True)
    published_youtube = Column(DateTime, nullable=True)
    published_instagram = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class AnnaVideo(Base):
    __tablename__ = "anna_videos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    production_status = Column(String, default="")
    published_tiktok = Column(DateTime, nullable=True)
    published_youtube = Column(DateTime, nullable=True)
    published_instagram = Column(DateTime, nullable=True)
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
