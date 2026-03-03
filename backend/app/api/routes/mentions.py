from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from app.database import get_db
from app.models.mention import Mention

router = APIRouter()


@router.get("/")
async def get_mentions(
    hours: int = Query(24),
    platform: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    is_crisis: Optional[bool] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """Liste des mentions avec filtres"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    conditions = [Mention.collected_at >= since]
    if platform:
        conditions.append(Mention.platform == platform)
    if sentiment:
        conditions.append(Mention.sentiment == sentiment)
    if is_crisis is not None:
        conditions.append(Mention.is_crisis == is_crisis)
    
    result = await db.execute(
        select(Mention)
        .where(and_(*conditions))
        .order_by(Mention.collected_at.desc())
        .offset(offset)
        .limit(limit)
    )
    mentions = result.scalars().all()
    
    return [
        {
            "id": m.id,
            "platform": m.platform,
            "content": m.content[:300] if m.content else None,
            "author": m.author,
            "sentiment": m.sentiment,
            "is_crisis": m.is_crisis,
            "narratifs": m.narratifs,
            "comentions": m.comentions,
            "collected_at": m.collected_at.isoformat() if m.collected_at else None,
            "url": m.url
        }
        for m in mentions
    ]


@router.get("/crisis")
async def get_crisis_mentions(
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """Mentions de crise uniquement"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    result = await db.execute(
        select(Mention)
        .where(and_(
            Mention.collected_at >= since,
            Mention.is_crisis == True
        ))
        .order_by(Mention.collected_at.desc())
        .limit(100)
    )
    mentions = result.scalars().all()
    
    return [
        {
            "id": m.id,
            "platform": m.platform,
            "content": m.content[:500] if m.content else None,
            "author": m.author,
            "crisis_keywords": m.crisis_keywords_found,
            "sentiment": m.sentiment,
            "collected_at": m.collected_at.isoformat() if m.collected_at else None,
            "url": m.url
        }
        for m in mentions
    ]


@router.get("/briefs")
async def get_daily_briefs(
    days: int = Query(7),
    db: AsyncSession = Depends(get_db)
):
    """Briefs quotidiens generes"""
    # Retourne les mentions avec daily_brief genere sur les X derniers jours
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(Mention.collected_at)
        .where(and_(
            Mention.collected_at >= since,
        ))
        .order_by(Mention.collected_at.desc())
    )
    # Structure de retour simplifiee - les briefs sont envoyes par email
    return {
        "message": "Les briefs quotidiens sont envoyes par email a l'equipe campaign",
        "period_days": days
    }


@router.get("/{mention_id}")
async def get_mention_detail(
    mention_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Detail d'une mention"""
    result = await db.execute(
        select(Mention).where(Mention.id == mention_id)
    )
    mention = result.scalar_one_or_none()
    
    if not mention:
        raise HTTPException(status_code=404, detail="Mention non trouvee")
    
    return {
        "id": mention.id,
        "platform": mention.platform,
        "content": mention.content,
        "author": mention.author,
        "author_followers": mention.author_followers,
        "sentiment": mention.sentiment,
        "sentiment_score": mention.sentiment_score,
        "narratifs": mention.narratifs,
        "comentions": mention.comentions,
        "is_crisis": mention.is_crisis,
        "crisis_keywords": mention.crisis_keywords_found,
        "collected_at": mention.collected_at.isoformat() if mention.collected_at else None,
        "url": mention.url,
        "engagement": mention.engagement_count
    }
