import asyncio
from apify_client import ApifyClient
from app.config import settings
from app.models.mention import Platform
from loguru import logger
from typing import List, Dict


class ApifyCollector:
    """
    Collecteur multi-plateformes via Apify.
    Couvre: TikTok, Instagram, Facebook, WhatsApp Channels.
    """

    ACTORS = {
        "tiktok": "clockworks/tiktok-scraper",
        "instagram": "apify/instagram-scraper",
        "facebook": "apify/facebook-pages-scraper",
        "whatsapp": "apify/web-scraper",
    }

    def __init__(self):
        self.client = ApifyClient(settings.APIFY_TOKEN)
        self.keywords = settings.keywords_list

    def _run_actor(self, actor_id: str, run_input: dict) -> list:
        """Synchronous Apify call — wrapped in to_thread() to avoid blocking event loop."""
        run = self.client.actor(actor_id).call(run_input=run_input)
        return list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

    async def collect_tiktok(self, max_results: int = 50) -> List[Dict]:
        """Collecter les videos TikTok mentionnant Wadagni."""
        mentions = []
        try:
            run_input = {
                "searchQueries": self.keywords,
                "maxResults": max_results,
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False,
            }
            # FIX: Apify SDK is synchronous — run in thread to avoid blocking the async event loop
            items = await asyncio.to_thread(self._run_actor, self.ACTORS["tiktok"], run_input)

            for item in items:
                content = item.get("text", "") or item.get("title", "")
                if not content:
                    continue

                mention = {
                    "platform": Platform.TIKTOK.value,
                    "platform_post_id": item.get("id"),
                    "url": item.get("webVideoUrl"),
                    "author": item.get("authorMeta", {}).get("name"),
                    "author_url": f"https://tiktok.com/@{item.get('authorMeta', {}).get('name')}",
                    "author_followers": item.get("authorMeta", {}).get("fans", 0),
                    "content": content,
                    "content_language": "fr",
                    "likes": item.get("diggCount", 0),
                    "shares": item.get("shareCount", 0),
                    "comments": item.get("commentCount", 0),
                    "views": item.get("playCount", 0),
                    "published_at": item.get("createTime"),
                    "raw_data": item,
                }
                mentions.append(mention)

            logger.info(f"TikTok: {len(mentions)} videos collectees")
        except Exception as e:
            logger.error(f"Erreur collecte TikTok: {e}")
        return mentions

    async def collect_instagram(self, max_results: int = 50) -> List[Dict]:
        """Collecter les posts Instagram mentionnant Wadagni."""
        mentions = []
        try:
            run_input = {
                "hashtags": ["wadagni", "romualdwadagni", "benin2026"],
                "resultsLimit": max_results,
                "resultsType": "posts",
            }
            # FIX: Run synchronous Apify call in thread
            items = await asyncio.to_thread(self._run_actor, self.ACTORS["instagram"], run_input)

            for item in items:
                caption = item.get("caption", "")
                if not caption:
                    continue
                if not any(k.lower() in caption.lower() for k in self.keywords):
                    continue

                mention = {
                    "platform": Platform.INSTAGRAM.value,
                    "platform_post_id": item.get("id"),
                    "url": item.get("url"),
                    "author": item.get("ownerUsername"),
                    "author_url": f"https://instagram.com/{item.get('ownerUsername')}",
                    "author_followers": item.get("ownerFollowersCount", 0),
                    "content": caption,
                    "content_language": "fr",
                    "likes": item.get("likesCount", 0),
                    "comments": item.get("commentsCount", 0),
                    "views": item.get("videoViewCount", 0),
                    "published_at": item.get("timestamp"),
                    "raw_data": item,
                }
                mentions.append(mention)

            logger.info(f"Instagram: {len(mentions)} posts collectes")
        except Exception as e:
            logger.error(f"Erreur collecte Instagram: {e}")
        return mentions

    async def collect_all(self) -> List[Dict]:
        """FIX: Collect from all platforms concurrently instead of sequentially."""
        tiktok, instagram = await asyncio.gather(
            self.collect_tiktok(),
            self.collect_instagram(),
            return_exceptions=True,
        )
        all_mentions = []
        for result in (tiktok, instagram):
            if isinstance(result, Exception):
                logger.error(f"Erreur collecte Apify: {result}")
            else:
                all_mentions.extend(result)

        logger.info(f"Apify total: {len(all_mentions)} mentions collectees")
        return all_mentions


apify_collector = ApifyCollector()
