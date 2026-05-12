from fastapi import APIRouter

from app.config import settings
from app.core.service_health import build_health_payload, get_core_services_status
from app.db.session import engine


router = APIRouter()


@router.get("/health/full", tags=["Health"])
async def health_full() -> dict[str, object]:
    services: dict[str, str] = {"api": "ok"}
    services.update(await get_core_services_status(engine))

    try:
        from app.scraper.browser import BrowserManager

        browser_manager = BrowserManager()
        try:
            await browser_manager._ensure_browser()
            services["playwright"] = "ok"
        except Exception:
            services["playwright"] = "unavailable"
        finally:
            try:
                await browser_manager.close()
            except Exception:
                pass
    except Exception:
        services["playwright"] = "unavailable"

    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            await client.models.list()
            services["openai"] = "ok"
        except Exception:
            services["openai"] = "unavailable"
    else:
        services["openai"] = "skipped"

    status = "ok" if all(value in {"ok", "skipped"} for value in services.values()) else "degraded"
    payload = build_health_payload(services)
    payload["status"] = status
    return payload
