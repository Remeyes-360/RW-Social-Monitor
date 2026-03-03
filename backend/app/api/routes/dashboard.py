from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.database import get_db
from app.models.mention import Mention

router = APIRouter()


@router.get("/stats")
async def get_stats(
    hours: int = Query(24, description="Periode en heures"),
    db: AsyncSession = Depends(get_db)
):
    """KPIs globaux: volume, sentiment, niveau alerte"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    result = await db.execute(
        select(Mention).where(Mention.collected_at >= since)
    )
    mentions = result.scalars().all()
    
    total = len(mentions)
    if total == 0:
        return {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "crisis": 0, "negative_pct": 0}
    
    positive = sum(1 for m in mentions if m.sentiment == "positif")
    negative = sum(1 for m in mentions if m.sentiment in ["negatif", "crise"])
    neutral = sum(1 for m in mentions if m.sentiment == "neutre")
    crisis = sum(1 for m in mentions if m.is_crisis)
    
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "crisis": crisis,
        "negative_pct": round(negative / total * 100, 1),
        "positive_pct": round(positive / total * 100, 1),
        "period_hours": hours
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
    rows = result.all()
    return [{"platform": r.platform, "count": r.count} for r in rows]


@router.get("/narratifs")
async def get_narratifs(
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """Top narratifs detectes"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    result = await db.execute(
        select(Mention).where(
            and_(Mention.collected_at >= since, Mention.narratifs != None)
        )
    )
    mentions = result.scalars().all()
    
    narratif_counts = {}
    for m in mentions:
        if m.narratifs:
            for n in m.narratifs:
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
            func.date_trunc('hour', Mention.collected_at).label("hour"),
            Mention.sentiment,
            func.count(Mention.id).label("count")
        )
        .where(Mention.collected_at >= since)
        .group_by(func.date_trunc('hour', Mention.collected_at), Mention.sentiment)
        .order_by(func.date_trunc('hour', Mention.collected_at))
    )
    rows = result.all()
    
    timeline = {}
    for r in rows:
        h = r.hour.isoformat()
        if h not in timeline:
            timeline[h] = {"hour": h, "positif": 0, "negatif": 0, "neutre": 0, "crise": 0}
        timeline[h][r.sentiment] = r.count
    
    return list(timeline.values())


@router.get("/top-accounts")
async def get_top_accounts(
    hours: int = Query(24),
    limit: int = Query(10),
    db: AsyncSession = Depends(get_db)
):
    """Comptes les plus actifs (moteurs de narratifs)"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    result = await db.execute(
        select(Mention.author, Mention.platform, func.count(Mention.id).label("count"))
        .where(and_(Mention.collected_at >= since, Mention.author != None))
        .group_by(Mention.author, Mention.platform)
        .order_by(func.count(Mention.id).desc())
        .limit(limit)
    )
    rows = result.all()
    return [{"author": r.author, "platform": r.platform, "count": r.count} for r in rows]


@router.get("/comentions")
async def get_comentions(
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """Co-mentions Wadagni/Talon et autres candidats"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    result = await db.execute(
        select(Mention).where(
            and_(
                Mention.collected_at >= since,
                Mention.comentions != None
            )
        )
    )
    mentions = result.scalars().all()
    
    comention_counts = {}
    for m in mentions:
        if m.comentions:
            for c in m.comentions:
                comention_counts[c] = comention_counts.get(c, 0) + 1
    
    sorted_comentions = sorted(comention_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"entity": e, "count": c} for e, c in sorted_comentions]


@router.get("/alert-level")
async def get_current_alert_level(
    db: AsyncSession = Depends(get_db)
):
    """Niveau d'alerte actuel"""
    since = datetime.now(timezone.utc) - timedelta(hours=2)
    
    result = await db.execute(
        select(Mention).where(Mention.collected_at >= since)
    )
    mentions = result.scalars().all()
    
    total = len(mentions)
    if total == 0:
        return {"level": "CALME", "negative_pct": 0, "crisis_count": 0}
    
    negative = sum(1 for m in mentions if m.sentiment in ["negatif", "crise"])
    crisis_count = sum(1 for m in mentions if m.is_crisis)
    negative_pct = negative / total * 100
    
    if crisis_count > 0 or negative_pct >= 60:
        level = "CRISE"
    elif negative_pct >= 40:
        level = "TENSION"
    elif negative_pct >= 20:
        level = "VIGILANCE"
    else:
        level = "CALME"
    
    return {
        "level": level,
        "negative_pct": round(negative_pct, 1),
        "crisis_count": crisis_count,
        "total_mentions": total
    }
