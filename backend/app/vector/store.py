from app.config import settings
from app.vector.index import FAISSIndexManager


_vector_store: FAISSIndexManager | None = None


def vector_store_enabled() -> bool:
    return bool(settings.ENABLE_VECTOR)


def get_vector_store() -> FAISSIndexManager | None:
    global _vector_store
    if not vector_store_enabled():
        return None
    try:
        if _vector_store is None:
            _vector_store = FAISSIndexManager()
        return _vector_store
    except Exception:
        return None
