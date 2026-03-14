from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.database import get_db
from app.models.mention import Mention, SentimentType
from app.auth import require_auth
from app.config import settings

router = APIRouter(dependencies=[require_auth])


def _alert_level_from_pct(negative_pct: float, crisis_count: int = 0) -> str:
    """FIX: Single centralized alert level calculation using settings thresholds.
    Previously this logic was duplicated in 3 places with 3 different threshold sets."""
    if crisis_count > 0 or negative_pct >= settings.ALERT_THRESHOLD_CRISIS:
        return "CRISE"
    elif negative_pct >= settings.ALERT_THRESHOLD_TENSION:
        return "TENSION"
    elif negative_pct >= settings.ALERT_THRESHOLD_VIGILANCE:
        return "VIGILANCE"
    return "CALME"


@router.get("/stats")
async def get_stats(
    hours: int = Query(24, description="Periode en heures"),
    db: AsyncSession = Depends(get_db)
):
    """FIX: KPIs now computed with SQL aggregation instead of loading all rows into Python."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(
            func.count(Mention.id).label("total"),
            func.sum(case((Mention.sentiment == SentimentType.POSITIVE, 1), else_=0)).label("positive"),
            func.sum(case((Mention.sentiment == SentimentType.NEGATIVE, 1), else_=0)).label("negative"),
            func.sum(case((Mention.sentiment == SentimentType.NEUTRAL, 1), else_=0)).label("neutral"),
            func.sum(case((Mention.sentiment == SentimentType.CRISIS, 1), else_=0)).label("crisis_sentiment"),
            func.sum(case((Mention.is_crisis == True, 1), else_=0)).label("crisis_flag"),
        ).where(Mention.collected_at >= since)
    )
    row = result.one()

    total = row.total or 0
    positive = row.positive or 0
    negative = (row.negative or 0) + (row.crisis_sentiment or 0)
    neutral = row.neutral or 0
    crisis = row.crisis_flag or 0

    if total == 0:
        return {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "crisis": 0,
                "negative_pct": 0, "positive_pct": 0, "period_hours": hours}

    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "crisis": crisis,
        "negative_pct": round(negative / total * 100, 1),
        "positive_pct": round(positive / total * 100, 1),
        "period_hours": hours,
    }


@router.get("/platforms")
async def get_platforms_breakdown(
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """Volume par plateforme"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(Mention.platform, func.count(Mention.id).label("count"))
        .where(Mention.collected_at >= since)
        .group_by(Mention.platform)
        .order_by(func.count(Mention.id).desc())
    )
    return [{"platform": r.platform, "count": r.count} for r in result.all()]


@router.get("/narratifs")
async def get_narratifs(
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """Top narratifs detectes"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(Mention.narratifs)
        .where(and_(Mention.collected_at >= since, Mention.narratifs.isnot(None)))
    )
    rows = result.scalars().all()

    narratif_counts: dict = {}
    for narratifs in rows:
        if narratifs:
            for n in narratifs:
                narratif_counts[n] = narratif_counts.get(n, 0) + 1

    sorted_narratifs = sorted(narratif_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"narratif": n, "count": c} for n, c in sorted_narratifs[:10]]


@router.get("/timeline")
async def get_timeline(
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """Evolution temporelle des mentions (par heure)"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(
            func.date_trunc("hour", Mention.collected_at).label("hour"),
            Mention.sentiment,
            func.count(Mention.id).label("count"),
        )
        .where(Mention.collected_at >= since)
        .group_by(func.date_trunc("hour", Mention.collected_at), Mention.sentiment)
        .order_by(func.date_trunc("hour", Mention.collected_at))
    )

    timeline: dict = {}
    for r in result.all():
        h = r.hour.isoformat()
        if h not in timeline:
            timeline[h] = {"hour": h, "positif": 0, "negatif": 0, "neutre": 0, "crise": 0}
        if r.sentiment:
            timeline[h][r.sentiment.value if hasattr(r.sentiment, "value") else r.sentiment] = r.count

    return list(timeline.values())


@router.get("/top-accounts")
async def get_top_accounts(
    hours: int = Query(24),
    limit: int = Query(10),
    db: AsyncSession = Depends(get_db)
):
    """Comptes les plus actifs"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(Mention.author, Mention.platform, func.count(Mention.id).label("count"))
        .where(and_(Mention.collected_at >= since, Mention.author.isnot(None)))
        .group_by(Mention.author, Mention.platform)
        .order_by(func.count(Mention.id).desc())
        .limit(limit)
    )
    return [{"author": r.author, "platform": r.platform, "count": r.count} for r in result.all()]


@router.get("/comentions")
async def get_comentions(
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """FIX: Now queries the comentions JSONB column that was added to the Mention model."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(Mention.comentions)
        .where(and_(
            Mention.collected_at >= since,
            Mention.comentions.isnot(None),
        ))
    )
    rows = result.scalars().all()

    comention_counts: dict = {}
    for comentions in rows:
        if comentions:
            for c in comentions:
                comention_counts[c] = comention_counts.get(c, 0) + 1

    sorted_comentions = sorted(comention_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"entity": e, "count": c} for e, c in sorted_comentions]


@router.get("/alert-level")
async def get_current_alert_level(
    db: AsyncSession = Depends(get_db)
):
    """FIX: Alert level now uses centralized thresholds from settings."""
    since = datetime.now(timezone.utc) - timedelta(hours=2)

    result = await db.execute(
        select(
            func.count(Mention.id).label("total"),
            func.sum(case(
                (Mention.sentiment.in_([SentimentType.NEGATIVE, SentimentType.CRISIS]), 1), else_=0
            )).label("negative"),
            func.sum(case((Mention.is_crisis == True, 1), else_=0)).label("crisis_count"),
        ).where(Mention.collected_at >= since)
    )
    row = result.one()

    total = row.total or 0
    if total == 0:
        return {"level": "CALME", "negative_pct": 0, "crisis_count": 0, "total_mentions": 0}

    negative_pct = (row.negative or 0) / total * 100
    crisis_count = row.crisis_count or 0
    level = _alert_level_from_pct(negative_pct, crisis_count)

    return {
        "level": level,
        "negative_pct": round(negative_pct, 1),
        "crisis_count": crisis_count,
        "total_mentions": total,
    }
