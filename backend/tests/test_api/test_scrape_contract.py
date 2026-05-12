import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_db
from app.main import create_app
from app.services.scrape_contract import (
    calculate_confidence,
    calculate_coverage,
    deduplicate_records,
    normalize_status,
    summarize_missing_fields,
)


pytestmark = pytest.mark.asyncio
TEST_API_KEY = "test-global-api-key"


def _override_db(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    return override_get_db


def _valid_payload() -> dict[str, object]:
    return {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 50,
        "fields": ["name", "contact", "email"],
    }


async def test_scrape_contract_accepts_valid_request(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=_valid_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["request_id"], str) and body["request_id"]
    assert body["status"] in {"completed", "partial", "failed"}
    assert isinstance(body["execution_time"], float)
    assert isinstance(body["total"], int)
    assert isinstance(body["data"], list)


async def test_scrape_contract_rejects_missing_api_key(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/scrape", json=_valid_payload())

    assert response.status_code == 401


async def test_scrape_contract_rejects_invalid_api_key(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": "invalid-contract-key"},
            json=_valid_payload(),
        )

    assert response.status_code == 403


async def test_scrape_contract_rejects_invalid_payload(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    invalid_payload = {
        "query": "",
        "location": "Saudi Arabia",
        "limit": -1,
        "fields": [],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=invalid_payload,
        )

    assert response.status_code == 422


async def test_scrape_contract_response_shape_is_stable(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=_valid_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"request_id", "status", "execution_time", "total", "data", "sources", "errors", "quality"}
    assert set(body["quality"].keys()) == {
        "duplicates_removed",
        "coverage",
        "confidence",
        "missing_fields",
        "normalized_fields",
    }


async def test_scrape_contract_routes_to_orchestrator_scrape_pipeline(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    captured_task_payload: dict[str, object] = {}

    class FakeOrchestrator:
        async def run(self, payload):
            captured_task_payload.update(payload)
            return {
                "task_type": "scrape",
                "status": "completed",
                "output_payload": {
                    "request_id": "req_contract_pipeline",
                    "execution_time": 0.42,
                    "data": [
                        {"name": "A", "contact": "111", "email": "a@example.com", "source": "source-1"},
                        {"name": "B", "contact": "222", "email": "b@example.com", "source": "source-2"},
                    ],
                    "sources": [
                        {"name": "source-1", "count": 1},
                        {"name": "source-2", "count": 1},
                    ],
                    "errors": [],
                    "quality": {
                        "duplicates_removed": 0,
                        "coverage": 1.0,
                        "confidence": 1.0,
                        "missing_fields": {"name": 0, "contact": 0, "email": 0},
                        "normalized_fields": 3,
                    },
                },
                "errors": [],
            }

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "_get_scrape_orchestrator", lambda: FakeOrchestrator())

    payload = {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 10,
        "fields": ["name", "contact", "email"],
        "source_type": "directory",
        "request_id": "req_contract_pipeline",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=payload,
        )

    assert response.status_code == 200
    body = response.json()
    assert captured_task_payload["task_type"] == "scrape"
    assert captured_task_payload["task_id"] == "req_contract_pipeline"
    assert captured_task_payload["input_payload"]["query"] == "hospitals"
    assert captured_task_payload["input_payload"]["location"] == "Saudi Arabia"
    assert captured_task_payload["input_payload"]["fields"] == ["name", "contact", "email"]
    assert captured_task_payload["input_payload"]["source_type"] == "directory"
    assert captured_task_payload["input_payload"]["request_id"] == "req_contract_pipeline"
    assert body["request_id"] == "req_contract_pipeline"
    assert body["status"] == "completed"
    assert body["total"] == 2
    assert body["data"] == [
        {"name": "A", "contact": "111", "email": "a@example.com", "source": "source-1"},
        {"name": "B", "contact": "222", "email": "b@example.com", "source": "source-2"},
    ]
    assert body["sources"] == [{"name": "source-1", "count": 1}, {"name": "source-2", "count": 1}]
    assert body["errors"] == []


async def test_scrape_contract_routes_url_requests_to_local_orchestrator_pipeline(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    captured_payload: dict[str, object] = {}

    class FakeOrchestrator:
        async def run(self, payload):
            captured_payload.update(payload)
            return {
                "status": "completed",
                "result": {
                    "data": [
                        {"name": "Alpha Clinic", "phone": "111"},
                    ],
                    "raw": {"final_url": "https://example.com/records"},
                    "processed": {"items": [{"name": "Alpha Clinic", "phone": "111"}]},
                    "analysis": {},
                    "vector": {},
                    "exports": {},
                },
                "execution": {
                    "validation": {
                        "status": "pass",
                        "confidence": 0.88,
                        "issues": [],
                        "metrics": {"fill_ratio": 0.75},
                        "should_retry": False,
                    }
                },
                "errors": [],
                "metadata": {
                    "duration_ms": 1450,
                },
            }

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "_get_scrape_orchestrator", lambda: FakeOrchestrator())

    payload = {
        "url": "https://example.com/records",
        "login_url": "https://example.com/login",
        "login_username": "demo-user",
        "login_password": "demo-pass",
        "query": "patients",
        "location": "Saudi Arabia",
        "limit": 10,
        "fields": ["name", "phone"],
        "source_type": "internal",
        "request_id": "req_local_url_pipeline",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=payload,
        )

    assert response.status_code == 200
    body = response.json()
    assert captured_payload["url"] == payload["url"]
    assert captured_payload["scrape_type"] == "structured"
    assert captured_payload["credentials"] == {
        "login_url": payload["login_url"],
        "username": payload["login_username"],
        "password": payload["login_password"],
    }
    assert captured_payload["config"]["prompt"] == payload["query"]
    assert captured_payload["config"]["fields"] == payload["fields"]
    assert captured_payload["strategy"]["record_fields"] == payload["fields"]
    assert "task_type" not in captured_payload
    assert body["status"] == "completed"
    assert body["total"] == 1
    assert body["data"] == [{"name": "Alpha Clinic", "phone": "111"}]
    assert body["sources"] == [{"name": "internal", "count": 1}]


async def test_scrape_contract_returns_failed_contract_when_orchestrator_raises(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    class FakeOrchestrator:
        async def run(self, payload):
            raise RuntimeError("upstream unavailable")

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "_get_scrape_orchestrator", lambda: FakeOrchestrator())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=_valid_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["total"] == 0
    assert body["data"] == []
    assert len(body["errors"]) == 1
    assert "upstream unavailable" in body["errors"][0]


async def test_scrape_contract_computes_real_quality_and_normalized_status(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    async def mock_run_pipeline(input_data):
        return {
            "request_id": "rq_123",
            "status": "completed",
            "execution_time": 1.234,
            "final_data": [
                {"name": "A", "contact": "111", "email": "a@example.com", "source": "source-1"},
                {"name": "A", "contact": "111", "email": "a@example.com", "source": "source-1"},
                {"name": "B", "contact": "", "email": "b@example.com", "source": "source-2"},
                {"name": "C", "contact": "333", "source": "source-2"},
            ],
            "sources": ["source-1", "source-2"],
            "errors": ["partial source timeout"],
        }

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "run_pipeline", mock_run_pipeline)

    payload = {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 10,
        "fields": ["name", "contact", "email"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=payload,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "rq_123"
    assert body["status"] == "partial"
    assert body["execution_time"] == 1.234
    assert body["total"] == 3
    assert body["quality"]["duplicates_removed"] == 1
    assert body["quality"]["coverage"] == pytest.approx(7 / 9)
    assert body["quality"]["missing_fields"] == {"name": 0, "contact": 1, "email": 1}
    assert body["quality"]["normalized_fields"] == 1
    assert body["quality"]["confidence"] == pytest.approx((7 / 9) * (1 / 3) * (1 / 3))
    assert body["sources"] == [{"name": "source-1", "count": 1}, {"name": "source-2", "count": 2}]


async def test_scrape_contract_generates_deterministic_request_id_when_missing(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    async def mock_run_pipeline(input_data):
        return {
            "status": "success",
            "final_data": [{"name": "A"}],
            "sources": [],
            "errors": [],
        }

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "run_pipeline", mock_run_pipeline)

    payload = {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 10,
        "fields": ["name"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=payload)
        second = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["request_id"].startswith("req_")
    assert first.json()["request_id"] == second.json()["request_id"]


async def test_health_endpoint_remains_integration_friendly(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "services" in body


async def test_scrape_contract_dedup_is_stable_regardless_of_requested_fields(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    final_data = [
        {"name": "Acme", "email": "INFO@acme.com", "contact": "111", "source": "s1"},
        {"name": " acme ", "email": " info@acme.com ", "contact": "999", "source": "s1"},
        {"name": "Acme", "email": "sales@acme.com", "contact": "111", "source": "s2"},
    ]

    async def mock_run_pipeline(input_data):
        return {
            "request_id": "rq_stable",
            "status": "completed",
            "execution_time": 0.5,
            "final_data": final_data,
            "sources": ["s1", "s2"],
            "errors": [],
        }

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "run_pipeline", mock_run_pipeline)

    payload_one = {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 10,
        "fields": ["name", "email"],
    }
    payload_two = {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 10,
        "fields": ["email", "contact"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=payload_one)
        second = await client.post("/api/v1/scrape", headers={"X-API-Key": TEST_API_KEY}, json=payload_two)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["total"] == 2
    assert second.json()["total"] == 2
    assert first.json()["quality"]["duplicates_removed"] == 1
    assert second.json()["quality"]["duplicates_removed"] == 1


async def test_scrape_contract_failed_status_when_no_usable_data_and_errors(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    async def mock_run_pipeline(input_data):
        return {
            "request_id": "rq_failed",
            "status": "completed",
            "execution_time": 0.1,
            "final_data": [],
            "sources": ["source-1"],
            "errors": ["all providers failed"],
        }

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "run_pipeline", mock_run_pipeline)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=_valid_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["status"] == "failed"


async def test_confidence_is_deterministic_for_fixed_inputs():
    inputs = {
        "coverage": 0.8,
        "total_records": 20,
        "duplicates_removed": 5,
        "missing_fields": {"name": 1, "email": 4, "contact": 8},
        "errors_count": 2,
    }
    c1 = calculate_confidence(**inputs)
    c2 = calculate_confidence(**inputs)
    assert c1 == c2
    assert 0.0 <= c1 <= 1.0


async def test_deduplicate_records_uses_fixed_priority_keys():
    records = [
        {"name": "Acme", "email": "INFO@acme.com", "contact": "111"},
        {"name": " acme ", "email": " info@acme.com ", "contact": "999"},
        {"name": "Acme", "email": "", "contact": "111"},
        {"title": "fallback", "value": "x"},
        {"title": "fallback ", "value": " x "},
    ]
    deduped_with_fields, removed_with_fields = deduplicate_records(records, ["contact"])
    deduped_without_fields, removed_without_fields = deduplicate_records(records, ["name", "email"])
    assert len(deduped_with_fields) == len(deduped_without_fields) == 3
    assert removed_with_fields == removed_without_fields == 2


async def test_coverage_uses_requested_field_opportunities():
    records = [
        {"name": "A", "email": "a@example.com", "contact": None},
        {"name": "B", "email": None, "contact": "123"},
    ]
    coverage = calculate_coverage(records, ["name", "email", "contact"])
    assert coverage == pytest.approx(4 / 6)


async def test_missing_fields_summary_counts_requested_fields():
    records = [
        {"name": "A", "email": "a@example.com", "contact": None},
        {"name": None, "email": None, "contact": "123"},
    ]
    missing = summarize_missing_fields(records, ["name", "email", "contact"])
    assert missing == {"name": 1, "email": 1, "contact": 1}


async def test_status_normalization_outputs_only_supported_values():
    assert normalize_status("completed", has_errors=False, total_records=2) == "completed"
    assert normalize_status("running", has_errors=False, total_records=2) == "partial"
    assert normalize_status("completed", has_errors=True, total_records=2) == "partial"
    assert normalize_status("failed", has_errors=False, total_records=2) == "failed"
    assert normalize_status("completed", has_errors=False, total_records=0) == "failed"


async def test_errors_are_always_human_readable_list(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = _override_db(session_factory)

    async def mock_run_pipeline(input_data):
        return {
            "request_id": "rq_error_shape",
            "status": "completed",
            "execution_time": 0.2,
            "final_data": [{"name": "A", "email": "a@example.com"}],
            "sources": ["source-1"],
            "errors": {"message": "upstream timeout"},
        }

    import app.api.v1.scrape as scrape_api

    monkeypatch.setattr(scrape_api, "run_pipeline", mock_run_pipeline)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/scrape",
            headers={"X-API-Key": TEST_API_KEY},
            json=_valid_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["errors"], list)
    assert body["errors"] == ["upstream timeout"]
