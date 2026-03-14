from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
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
    status = Column(String, default="extracted")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    video = relationship("Video", back_populates="script")


class PresetQuery(Base):
    __tablename__ = "preset_queries"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    query = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
