from telethon import TelegramClient, events
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterEmpty
from app.config import settings
from app.models.mention import Platform
from loguru import logger
from typing import List, Dict
import asyncio

# Canaux Telegram beninois a surveiller
BENIN_CHANNELS = [
    "beninwebtv",
    "fraternitematinbenin",
    "lanationbenin",
    "beninrevele",
    "actu_benin",
    "politiquebenin",
    "benin2026",
    # Ajouter d'autres canaux pertinents
]


class TelegramCollector:
    """Collecteur de mentions Telegram pour Romuald Wadagni."""

    def __init__(self):
        self.client = TelegramClient(
            "rw_monitor_session",
            api_id=int(settings.TELEGRAM_API_ID) if settings.TELEGRAM_API_ID else 0,
            api_hash=settings.TELEGRAM_API_HASH,
        )
        self.keywords = settings.keywords_list
        self.channels = BENIN_CHANNELS

    async def collect(self, limit: int = 50) -> List[Dict]:
        """Collecter les messages Telegram mentionnant Wadagni."""
        mentions = []

        try:
            if settings.TELEGRAM_SESSION_STRING:
                # Utiliser session string si disponible
                from telethon.sessions import StringSession
                self.client = TelegramClient(
                    StringSession(settings.TELEGRAM_SESSION_STRING),
                    api_id=int(settings.TELEGRAM_API_ID),
                    api_hash=settings.TELEGRAM_API_HASH,
                )

            async with self.client:
                for channel in self.channels:
                    try:
                        entity = await self.client.get_entity(channel)
                        
                        async for message in self.client.iter_messages(
                            entity, limit=limit, search=" OR ".join(self.keywords)
                        ):
                            if not message.text:
                                continue

                            # Verifier si le message contient un mot cle
                            content_lower = message.text.lower()
                            if not any(k.lower() in content_lower for k in self.keywords):
                                continue

                            mention = {
                                "platform": Platform.TELEGRAM.value,
                                "platform_post_id": f"{channel}_{message.id}",
                                "url": f"https://t.me/{channel}/{message.id}",
                                "author": channel,
                                "author_url": f"https://t.me/{channel}",
                                "author_followers": getattr(entity, 'participants_count', 0) or 0,
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
