from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "RW Social Monitor"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Base de donnees
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Securite
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")

    # Twitter / X
    TWITTER_BEARER_TOKEN: str = Field(default="", env="TWITTER_BEARER_TOKEN")
    TWITTER_API_KEY: str = Field(default="", env="TWITTER_API_KEY")
    TWITTER_API_SECRET: str = Field(default="", env="TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN: str = Field(default="", env="TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET: str = Field(default="", env="TWITTER_ACCESS_SECRET")

    # Facebook / Instagram
    FACEBOOK_APP_ID: str = Field(default="", env="FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET: str = Field(default="", env="FACEBOOK_APP_SECRET")
    FACEBOOK_ACCESS_TOKEN: str = Field(default="", env="FACEBOOK_ACCESS_TOKEN")

    # YouTube
    YOUTUBE_API_KEY: str = Field(default="", env="YOUTUBE_API_KEY")

    # Telegram
    TELEGRAM_API_ID: str = Field(default="", env="TELEGRAM_API_ID")
    TELEGRAM_API_HASH: str = Field(default="", env="TELEGRAM_API_HASH")
    TELEGRAM_PHONE: str = Field(default="", env="TELEGRAM_PHONE")
    TELEGRAM_SESSION_STRING: str = Field(default="", env="TELEGRAM_SESSION_STRING")

    # Apify
    APIFY_TOKEN: str = Field(default="", env="APIFY_TOKEN")

    # Alertes Email
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: str = Field(default="", env="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")
    ALERT_RECIPIENTS: str = Field(default="", env="ALERT_RECIPIENTS")

    # FIX: Centralized alert thresholds (previously split across 3 files with conflicting values)
    ALERT_THRESHOLD_CALM: int = Field(default=20, env="ALERT_THRESHOLD_CALM")
    ALERT_THRESHOLD_VIGILANCE: int = Field(default=40, env="ALERT_THRESHOLD_VIGILANCE")
    ALERT_THRESHOLD_TENSION: int = Field(default=60, env="ALERT_THRESHOLD_TENSION")
    ALERT_THRESHOLD_CRISIS: int = Field(default=80, env="ALERT_THRESHOLD_CRISIS")

    ALERT_VOLUME_SPIKE_MULTIPLIER: int = Field(default=3, env="ALERT_VOLUME_SPIKE_MULTIPLIER")
    ALERT_CRISIS_KEYWORDS: str = Field(
        default="CRIET,arrestation,scandale,corruption,prison",
        env="ALERT_CRISIS_KEYWORDS"
    )

    # Configuration moniteur
    MONITOR_KEYWORDS: str = Field(
        default="Romuald Wadagni,RWadagni,Wadagni,wadagni2026",
        env="MONITOR_KEYWORDS"
    )
    MONITOR_LANGUAGES: str = Field(default="fr,fon,yoruba", env="MONITOR_LANGUAGES")
    COLLECT_INTERVAL_MINUTES: int = Field(default=15, env="COLLECT_INTERVAL_MINUTES")

    # FIX: Max concurrent AI analysis calls (prevents N*GPT-4 sequential blowout)
    AI_ANALYSIS_CONCURRENCY: int = Field(default=10, env="AI_ANALYSIS_CONCURRENCY")

    @property
    def keywords_list(self) -> List[str]:
        return [k.strip() for k in self.MONITOR_KEYWORDS.split(",")]

    @property
    def crisis_keywords_list(self) -> List[str]:
        return [k.strip() for k in self.ALERT_CRISIS_KEYWORDS.split(",")]

    @property
    def alert_recipients_list(self) -> List[str]:
        return [r.strip() for r in self.ALERT_RECIPIENTS.split(",") if r.strip()]

    @property
    def monitor_languages_list(self) -> List[str]:
        return [lang.strip() for lang in self.MONITOR_LANGUAGES.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
