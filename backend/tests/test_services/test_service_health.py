import pytest

from app.core import service_health


@pytest.mark.asyncio
async def test_assert_redis_broker_available_passes_when_ping_succeeds(monkeypatch):
    class _HealthyRedis:
        @classmethod
        def from_url(cls, *args, **kwargs):
            return cls()

        async def ping(self):
            return True

        async def aclose(self):
            return None

    monkeypatch.setattr(service_health, "Redis", _HealthyRedis)

    await service_health.assert_redis_broker_available()


@pytest.mark.asyncio
async def test_assert_redis_broker_available_raises_clear_error_when_unreachable(monkeypatch):
    class _FailingRedis:
        @classmethod
        def from_url(cls, *args, **kwargs):
            return cls()

        async def ping(self):
            raise RuntimeError("cannot reach redis")

        async def aclose(self):
            return None

    monkeypatch.setattr(service_health, "Redis", _FailingRedis)
    monkeypatch.setattr(service_health.settings, "REDIS_URL", "redis://127.0.0.1:46379/0")
    monkeypatch.setattr(service_health.settings, "ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="Redis broker unreachable at redis://127.0.0.1:46379/0"):
        await service_health.assert_redis_broker_available()
