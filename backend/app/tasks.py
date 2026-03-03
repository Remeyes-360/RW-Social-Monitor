from app.celery_app import celery_app, run_async
from app.collectors.twitter_collector import twitter_collector
from app.collectors.telegram_collector import telegram_collector
from app.collectors.apify_collector import apify_collector
from app.analyzers.sentiment_analyzer import analyze_mention, generate_daily_brief, generate_weekly_report
from app.alerts.alert_manager import alert_manager
from app.database import AsyncSessionLocal
from app.models.mention import Mention
from sqlalchemy import select, func, cast, Float
from datetime import datetime, timedelta, timezone
from loguru import logger
from typing import List, Dict
import asyncio


async def save_mentions(mentions: List[Dict]) -> int:
    """Sauvegarder les mentions en base de donnees."""
    saved = 0
    async with AsyncSessionLocal() as db:
        for data in mentions:
            # Verifier si la mention existe deja
            existing = await db.execute(
                select(Mention).where(
                    Mention.platform_post_id == data.get("platform_post_id")
                )
            )
            if existing.scalar_one_or_none():
                continue  # Deja en base

            # Analyser avec l'IA
            analysis = await analyze_mention(
                content=data["content"],
                platform=data["platform"],
            )

            # Creer l'objet Mention
            mention = Mention(
                platform=data["platform"],
                platform_post_id=data.get("platform_post_id"),
                url=data.get("url"),
                author=data.get("author"),
                author_url=data.get("author_url"),
                author_followers=data.get("author_followers", 0),
                content=data["content"],
                content_language=data.get("content_language", "fr"),
                likes=data.get("likes", 0),
                shares=data.get("shares", 0),
                comments=data.get("comments", 0),
                views=data.get("views", 0),
                published_at=data.get("published_at"),
                # Resultats IA
                sentiment=analysis.get("sentiment"),
                sentiment_score=analysis.get("sentiment_score"),
                narratifs=analysis.get("narratifs", []),
                keywords=analysis.get("keywords", []),
                is_talon_comention=analysis.get("is_talon_comention", False),
                is_rumor=analysis.get("is_rumor", False),
                is_crisis=analysis.get("is_crisis", False),
                crisis_keywords_found=analysis.get("crisis_keywords_found", []),
                ai_summary=analysis.get("summary_fr"),
                processed=True,
                raw_data=data.get("raw_data", {}),
            )
            db.add(mention)
            saved += 1

        await db.commit()
    return saved


@celery_app.task(name="app.tasks.collect_all_platforms", bind=True, max_retries=3)
def collect_all_platforms(self):
    """Tache principale: collecter les mentions sur toutes les plateformes."""
    logger.info("Demarrage collecte multi-plateformes...")
    
    async def _collect():
        all_mentions = []

        # Twitter / X
        try:
            twitter = await twitter_collector.collect()
            all_mentions.extend(twitter)
        except Exception as e:
            logger.error(f"Erreur Twitter: {e}")

        # Telegram
        try:
            telegram = await telegram_collector.collect()
            all_mentions.extend(telegram)
        except Exception as e:
            logger.error(f"Erreur Telegram: {e}")

        # Apify (TikTok + Instagram)
        try:
            apify = await apify_collector.collect_all()
            all_mentions.extend(apify)
        except Exception as e:
            logger.error(f"Erreur Apify: {e}")

        # Sauvegarder et analyser
        saved = await save_mentions(all_mentions)
        logger.info(f"Collecte terminee: {len(all_mentions)} collectees, {saved} nouvelles sauvegardees")
        return saved

    return run_async(_collect())


@celery_app.task(name="app.tasks.generate_daily_brief_task")
def generate_daily_brief_task():
    """Generer et envoyer le brief quotidien au QG."""
    async def _brief():
        async with AsyncSessionLocal() as db:
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            result = await db.execute(
                select(Mention).where(Mention.collected_at >= since)
            )
            mentions = result.scalars().all()

            if not mentions:
                logger.info("Pas de mentions pour le brief quotidien")
                return

            # Preparer les donnees pour l'IA
            data = [{
                "platform": m.platform,
                "sentiment": m.sentiment,
                "narratifs": m.narratifs,
                "keywords": m.keywords,
                "summary": m.ai_summary,
                "is_crisis": m.is_crisis,
                "is_talon": m.is_talon_comention,
            } for m in mentions]

            brief = await generate_daily_brief(data)

            # Envoyer par email
            await alert_manager.send_email_alert(
                subject=f"Brief Meteo Numerique - {datetime.now().strftime('%d/%m/%Y')}",
                body=brief,
                alert_level="CALME",
            )
            logger.info("Brief quotidien envoye")

    return run_async(_brief())


@celery_app.task(name="app.tasks.check_and_trigger_alerts")
def check_and_trigger_alerts():
    """Verifier les seuils d'alerte et declencher si necessaire."""
    async def _check():
        async with AsyncSessionLocal() as db:
            since = datetime.now(timezone.utc) - timedelta(hours=2)
            result = await db.execute(
                select(Mention).where(Mention.collected_at >= since)
            )
            recent = result.scalars().all()

            if not recent:
                return

            total = len(recent)
            negative = sum(1 for m in recent if m.sentiment in ["negatif", "crise"])
            crisis = [m for m in recent if m.is_crisis]

            negative_pct = (negative / total * 100) if total > 0 else 0
            level = alert_manager.calculate_alert_level(negative_pct)

            logger.info(f"Check alertes: {total} mentions, {negative_pct:.0f}% negatif, niveau={level}")

            # Alerte crise
            if crisis:
                crisis_data = [{
                    "content": m.content[:200],
                    "platform": m.platform,
                    "crisis_keywords": m.crisis_keywords_found,
                } for m in crisis[:5]]
                await alert_manager.trigger_crisis_alert(crisis_data, f"{len(crisis)} contenus de crise detectes")

    return run_async(_check())


@celery_app.task(name="app.tasks.generate_weekly_report_task")
def generate_weekly_report_task():
    """Generer le rapport strategique hebdomadaire."""
    logger.info("Generation rapport hebdomadaire...")
    # Implemente de facon similaire au brief quotidien mais sur 7 jours
    pass
