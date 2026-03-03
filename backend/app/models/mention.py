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
    sentiment = Column(Enum(SentimentType), nullable=True)
    sentiment_score = Column(Float, nullable=True)  # -1.0 a 1.0
    narratifs = Column(JSONB, default=list)  # Liste des narratifs detectes
    keywords = Column(JSONB, default=list)  # Mots cles extraits
    is_talon_comention = Column(Boolean, default=False)  # Co-mention avec Talon
    is_rumor = Column(Boolean, default=False)  # Detection rumeur
    is_crisis = Column(Boolean, default=False)  # Alerte crise
    crisis_keywords_found = Column(JSONB, default=list)
    ai_summary = Column(Text, nullable=True)  # Resume IA
    
    # Metadata
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    processed = Column(Boolean, default=False)
    raw_data = Column(JSONB, default=dict)  # Donnees brutes originales

    def __repr__(self):
        return f"<Mention platform={self.platform} sentiment={self.sentiment}>"
