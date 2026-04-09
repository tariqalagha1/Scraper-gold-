from celery import Celery

from app.config import settings


def create_celery_app() -> Celery:
    app = Celery(
        "smart_scraper",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=["app.queue.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        result_expires=3600,
        task_default_queue="scraper.default",
        broker_connection_retry_on_startup=True,
        broker_transport_options={"visibility_timeout": settings.CELERY_TASK_TIME_LIMIT * 2},
        task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
        task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
        task_default_retry_delay=2,
        task_annotations={"*": {"max_retries": 3}},
    )
    return app


celery_app = create_celery_app()
