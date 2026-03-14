from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum


class Platform(str, enum.Enum):
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    PRESS = "press"


class SentimentType(str, enum.Enum):
    POSITIVE = "positif"
    NEUTRAL = "neutre"
    NEGATIVE = "negatif"
    CRISIS = "crise"


class Mention(Base):
    __tablename__ = "mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(Enum(Platform), nullable=False, index=True)
    platform_post_id = Column(String(255), unique=True, nullable=True)
    url = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    author_url = Column(Text, nullable=True)
    author_followers = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    content_language = Column(String(10), default="fr")

    # Metrics
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    views = Column(Integer, default=0)
    reach_estimate = Column(Integer, default=0)

    # Analyse IA
    # FIX: Added index=True on sentiment and is_crisis — most-filtered columns lacked indexes
    sentiment = Column(Enum(SentimentType), nullable=True, index=True)
    sentiment_score = Column(Float, nullable=True)  # -1.0 a 1.0
    narratifs = Column(JSONB, default=list)
    keywords = Column(JSONB, default=list)
    # FIX: Added comentions column — was referenced in dashboard.py but missing from model
    comentions = Column(JSONB, default=list)
    is_talon_comention = Column(Boolean, default=False)
    is_rumor = Column(Boolean, default=False)
    # FIX: Added index=True on is_crisis
    is_crisis = Column(Boolean, default=False, index=True)
    crisis_keywords_found = Column(JSONB, default=list)
    ai_summary = Column(Text, nullable=True)

    # Metadata
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    processed = Column(Boolean, default=False)
    raw_data = Column(JSONB, default=dict)

    @property
    def engagement_count(self) -> int:
        """FIX: Added computed engagement_count property — was referenced in route but missing."""
        return (self.likes or 0) + (self.shares or 0) + (self.comments or 0)

    def __repr__(self):
        return f"<Mention platform={self.platform} sentiment={self.sentiment}>"
