import pytest
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.testclient import TestClient

from app.api.v1.scrape import router as scrape_router

# ---------------------------------------------------------
# Mocks for Isolated Contract Testing
# ---------------------------------------------------------
async def mock_verify_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")):
    """Mocks the exact auth enforcement defined in the requirements"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    if x_api_key != "valid_integration_key":
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return "valid_integration_key"

# Setup test app to map both /health and /api/v1/scrape
app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Override dependencies safely for this test app scope
app.include_router(
    scrape_router, 
    prefix="/api/v1/scrape", 
    dependencies=[Depends(mock_verify_api_key)]
)

client = TestClient(app)

# ---------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_scrape_missing_api_key():
    response = client.post("/api/v1/scrape", json={"query": "hospitals"})
    assert response.status_code == 401
    assert "Missing API Key" in response.json()["detail"]

def test_scrape_invalid_api_key():
    response = client.post(
        "/api/v1/scrape", 
        headers={"X-API-Key": "invalid_key"}, 
        json={"query": "hospitals"}
    )
    assert response.status_code == 403
    assert "Invalid API Key" in response.json()["detail"]

def test_scrape_invalid_payload():
    # Missing required 'query' field
    response = client.post(
        "/api/v1/scrape",
        headers={"X-API-Key": "valid_integration_key"},
        json={"location": "Saudi Arabia", "limit": 50}
    )
    assert response.status_code == 422 # FastAPI validation rejection

def test_scrape_valid_request_and_contract():
    payload = {
        "query": "hospitals",
        "location": "Saudi Arabia",
        "limit": 50,
        "fields": ["name", "contact", "email"]
    }
    response = client.post(
        "/api/v1/scrape",
        headers={"X-API-Key": "valid_integration_key"},
        json=payload
    )
    assert response.status_code == 200
    data = response.json()
    
    # Verify exact contract shape is respected
    expected_keys = {"status", "total", "data", "sources", "errors", "quality"}
    assert set(data.keys()) == expected_keys
    
    # Verify quality layer matches structure
    quality = data["quality"]
    expected_quality_keys = {"duplicates_removed", "coverage", "normalized_fields_count"}
    assert set(quality.keys()) == expected_quality_keys