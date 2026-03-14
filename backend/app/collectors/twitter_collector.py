import tweepy
from app.config import settings
from app.models.mention import Platform
from loguru import logger
from datetime import datetime, timezone
from typing import List, Dict

# Twitter language codes supported by the API
# Fon does not have an ISO 639-1 code recognised by Twitter; Yoruba = 'yo'
_TWITTER_LANG_MAP = {"fr": "fr", "yoruba": "yo", "fon": None}


class TwitterCollector:
    """Collecteur de mentions X/Twitter pour Romuald Wadagni."""

    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=settings.TWITTER_BEARER_TOKEN,
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_SECRET,
            wait_on_rate_limit=True,
        )
        self.keywords = settings.keywords_list

    def build_query(self) -> str:
        """
        FIX: Build language filter from MONITOR_LANGUAGES setting.
        Previously hardcoded to lang:fr, silently dropping Fon and Yoruba content.
        Fon has no Twitter language code so no lang filter is applied when it is
        the only non-mappable language (falls back to no language restriction).
        """
        keyword_parts = [f'"{k}"' for k in self.keywords]
        query = " OR ".join(keyword_parts)
        query += " -is:retweet"

        supported_lang_codes = [
            _TWITTER_LANG_MAP[lang]
            for lang in settings.monitor_languages_list
            if lang in _TWITTER_LANG_MAP and _TWITTER_LANG_MAP[lang] is not None
        ]

        if supported_lang_codes:
            if len(supported_lang_codes) == 1:
                query += f" lang:{supported_lang_codes[0]}"
            else:
                lang_filter = " OR ".join(f"lang:{c}" for c in supported_lang_codes)
                query += f" ({lang_filter})"
        # If no mappable language codes, omit lang filter entirely to catch all languages

        return query

    async def collect(self, max_results: int = 100) -> List[Dict]:
        """Collecter les tweets mentionnant Wadagni."""
        mentions = []
        query = self.build_query()

        try:
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["created_at", "author_id", "public_metrics", "lang", "referenced_tweets", "entities"],
                user_fields=["name", "username", "public_metrics", "url"],
                expansions=["author_id"],
            )

            if not tweets.data:
                logger.info("Aucun tweet trouve")
                return []

            users = {u.id: u for u in (tweets.includes.get("users") or [])}

            for tweet in tweets.data:
                user = users.get(tweet.author_id)
                metrics = tweet.public_metrics or {}

                mention = {
                    "platform": Platform.TWITTER.value,
                    "platform_post_id": str(tweet.id),
                    "url": f"https://x.com/i/web/status/{tweet.id}",
                    "author": user.username if user else "unknown",
                    "author_url": f"https://x.com/{user.username}" if user else None,
                    "author_followers": user.public_metrics.get("followers_count", 0) if user and user.public_metrics else 0,
                    "content": tweet.text,
                    "content_language": tweet.lang or "fr",
                    "likes": metrics.get("like_count", 0),
                    "shares": metrics.get("retweet_count", 0),
                    "comments": metrics.get("reply_count", 0),
                    "views": metrics.get("impression_count", 0),
                    "published_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "raw_data": {"tweet_id": str(tweet.id), "metrics": metrics},
                }
                mentions.append(mention)

            logger.info(f"Twitter: {len(mentions)} tweets collectes")
            return mentions

        except tweepy.TooManyRequests:
            logger.warning("Twitter: Limite de taux atteinte")
            return []
        except Exception as e:
            logger.error(f"Erreur collecte Twitter: {e}")
            return []


twitter_collector = TwitterCollector()
