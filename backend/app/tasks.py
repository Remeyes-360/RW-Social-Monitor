from app.celery_app import celery_app, run_async
from app.collectors.twitter_collector import twitter_collector
from app.collectors.telegram_collector import telegram_collector
from app.collectors.apify_collector import apify_collector
# FIX: generate_weekly_report now exists in sentiment_analyzer — import no longer crashes worker
from app.analyzers.sentiment_analyzer import analyze_mention, generate_daily_brief, generate_weekly_report
from app.alerts.alert_manager import alert_manager
from app.database import AsyncSessionLocal
from app.models.mention import Mention
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from loguru import logger
from typing import List, Dict
import asyncio


async def save_mentions(mentions: List[Dict]) -> int:
    """
    FIX: AI analysis is now concurrent with a semaphore instead of sequential.
    Previously: 100 mentions = 100 sequential GPT-4 calls (very slow, expensive).
    Now: up to AI_ANALYSIS_CONCURRENCY calls run in parallel.
    """
    from app.config import settings

    if not mentions:
        return 0

    # Deduplicate against DB in one query
    post_ids = [m.get("platform_post_id") for m in mentions if m.get("platform_post_id")]
    async with AsyncSessionLocal() as db:
        existing_result = await db.execute(
            select(Mention.platform_post_id).where(Mention.platform_post_id.in_(post_ids))
        )
        existing_ids = {row[0] for row in existing_result.all()}

    new_mentions = [m for m in mentions if m.get("platform_post_id") not in existing_ids
                    and m.get("platform_post_id") is not None]

    if not new_mentions:
        logger.info("Aucune nouvelle mention a sauvegarder")
        return 0

    # FIX: Concurrent AI analysis with semaphore
    semaphore = asyncio.Semaphore(settings.AI_ANALYSIS_CONCURRENCY)

    async def analyze_with_semaphore(data: Dict) -> tuple[Dict, Dict]:
        async with semaphore:
            analysis = await analyze_mention(
                content=data["content"],
                platform=data["platform"],
            )
            return data, analysis

    results = await asyncio.gather(
        *[analyze_with_semaphore(m) for m in new_mentions],
        return_exceptions=True,
    )

    saved = 0
    async with AsyncSessionLocal() as db:
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Erreur lors de l'analyse d'une mention: {result}")
                continue

            data, analysis = result
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
                sentiment=analysis.get("sentiment"),
                sentiment_score=analysis.get("sentiment_score"),
                narratifs=analysis.get("narratifs", []),
                keywords=analysis.get("keywords", []),
                comentions=analysis.get("comentions", []),
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

    logger.info(f"Sauvegarde: {saved} nouvelles mentions")
    return saved


@celery_app.task(name="app.tasks.collect_all_platforms", bind=True, max_retries=3)
def collect_all_platforms(self):
    """Tache principale: collecter les mentions sur toutes les plateformes."""
    logger.info("Demarrage collecte multi-plateformes...")

    async def _collect():
        all_mentions = []

        try:
            twitter = await twitter_collector.collect()
            all_mentions.extend(twitter)
        except Exception as e:
            logger.error(f"Erreur Twitter: {e}")

        try:
            telegram = await telegram_collector.collect()
            all_mentions.extend(telegram)
        except Exception as e:
            logger.error(f"Erreur Telegram: {e}")

        try:
            apify = await apify_collector.collect_all()
            all_mentions.extend(apify)
        except Exception as e:
            logger.error(f"Erreur Apify: {e}")

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

            if crisis:
                crisis_data = [{
                    "content": m.content[:200],
                    "platform": m.platform,
                    "crisis_keywords": m.crisis_keywords_found,
                } for m in crisis[:5]]
                await alert_manager.trigger_crisis_alert(
                    crisis_data, f"{len(crisis)} contenus de crise detectes"
                )

    return run_async(_check())


# FIX: Implemented weekly report — was a silent pass before
@celery_app.task(name="app.tasks.generate_weekly_report_task")
def generate_weekly_report_task():
    """Generer et envoyer le rapport strategique hebdomadaire au QG."""
    logger.info("Generation rapport hebdomadaire...")

    async def _weekly():
        async with AsyncSessionLocal() as db:
            since = datetime.now(timezone.utc) - timedelta(days=7)
            result = await db.execute(
                select(Mention).where(Mention.collected_at >= since)
            )
            mentions = result.scalars().all()

            if not mentions:
                logger.info("Pas de mentions pour le rapport hebdomadaire")
                return

            data = [{
                "platform": m.platform,
                "sentiment": m.sentiment,
                "sentiment_score": m.sentiment_score,
                "narratifs": m.narratifs,
                "keywords": m.keywords,
                "summary": m.ai_summary,
                "is_crisis": m.is_crisis,
                "is_talon": m.is_talon_comention,
                "is_rumor": m.is_rumor,
                "published_at": m.published_at.isoformat() if m.published_at else None,
            } for m in mentions]

            report = await generate_weekly_report(data)

            week_label = datetime.now().strftime("Semaine %W - %Y")
            await alert_manager.send_email_alert(
                subject=f"Rapport Hebdomadaire - {week_label}",
                body=report,
                alert_level="CALME",
            )
            logger.info(f"Rapport hebdomadaire envoye: {len(mentions)} mentions analysees")

    return run_async(_weekly())
