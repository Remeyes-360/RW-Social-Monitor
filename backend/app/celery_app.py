from celery import Celery
from celery.schedules import crontab
from app.config import settings
from loguru import logger
import asyncio

# Initialisation Celery
celery_app = Celery(
    "rw_monitor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Porto-Novo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Planification des taches periodiques
    beat_schedule={
        # Collecte toutes les 15 minutes
        "collect-mentions": {
            "task": "app.tasks.collect_all_platforms",
            "schedule": settings.COLLECT_INTERVAL_MINUTES * 60,  # en secondes
            "options": {"queue": "collect"},
        },
        # Brief quotidien a 7h WAT
        "daily-brief": {
            "task": "app.tasks.generate_daily_brief_task",
            "schedule": crontab(hour=7, minute=0),
            "options": {"queue": "reports"},
        },
        # Note hebdomadaire le lundi a 8h WAT
        "weekly-report": {
            "task": "app.tasks.generate_weekly_report_task",
            "schedule": crontab(hour=8, minute=0, day_of_week=1),
            "options": {"queue": "reports"},
        },
        # Verification alertes toutes les 5 minutes
        "check-alerts": {
            "task": "app.tasks.check_and_trigger_alerts",
            "schedule": 300,  # 5 minutes
            "options": {"queue": "alerts"},
        },
    },
    task_queues={
        "collect": {},
        "analyze": {},
        "alerts": {},
        "reports": {},
    },
    task_default_queue="collect",
)


def run_async(coro):
    """Helper pour executer du code async dans les taches Celery sync."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
