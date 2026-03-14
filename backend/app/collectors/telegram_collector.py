from telethon import TelegramClient
from telethon.sessions import StringSession
from app.config import settings
from app.models.mention import Platform
from loguru import logger
from typing import List, Dict

BENIN_CHANNELS = [
    "beninwebtv",
    "fraternitematinbenin",
    "lanationbenin",
    "beninrevele",
    "actu_benin",
    "politiquebenin",
    "benin2026",
]


class TelegramCollector:
    """Collecteur de mentions Telegram pour Romuald Wadagni."""

    def __init__(self):
        # FIX: Always use StringSession from env — file-based session leaked credentials
        # and lost auth on container restart.
        if not settings.TELEGRAM_SESSION_STRING:
            raise RuntimeError(
                "TELEGRAM_SESSION_STRING must be set. "
                "Run `python -c 'from telethon.sync import TelegramClient; "
                "from telethon.sessions import StringSession; "
                "print(TelegramClient(StringSession(), API_ID, API_HASH).start().session.save())'` "
                "to generate a session string."
            )
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set.")

        self.client = TelegramClient(
            StringSession(settings.TELEGRAM_SESSION_STRING),
            api_id=int(settings.TELEGRAM_API_ID),
            api_hash=settings.TELEGRAM_API_HASH,
        )
        self.keywords = settings.keywords_list
        self.channels = BENIN_CHANNELS

    async def collect(self, limit: int = 50) -> List[Dict]:
        """Collecter les messages Telegram mentionnant Wadagni."""
        mentions = []

        try:
            async with self.client:
                for channel in self.channels:
                    try:
                        entity = await self.client.get_entity(channel)

                        async for message in self.client.iter_messages(
                            entity, limit=limit, search=" OR ".join(self.keywords)
                        ):
                            if not message.text:
                                continue

                            content_lower = message.text.lower()
                            if not any(k.lower() in content_lower for k in self.keywords):
                                continue

                            mention = {
                                "platform": Platform.TELEGRAM.value,
                                "platform_post_id": f"{channel}_{message.id}",
                                "url": f"https://t.me/{channel}/{message.id}",
                                "author": channel,
                                "author_url": f"https://t.me/{channel}",
                                "author_followers": getattr(entity, "participants_count", 0) or 0,
                                "content": message.text,
                                "content_language": "fr",
                                "views": message.views or 0,
                                "shares": message.forwards or 0,
                                "published_at": message.date.isoformat() if message.date else None,
                                "raw_data": {"channel": channel, "message_id": message.id},
                            }
                            mentions.append(mention)

                    except Exception as e:
                        logger.warning(f"Telegram: Erreur canal {channel}: {e}")
                        continue

            logger.info(f"Telegram: {len(mentions)} messages collectes")
            return mentions

        except Exception as e:
            logger.error(f"Erreur collecte Telegram: {e}")
            return []


telegram_collector = TelegramCollector()
