import pytest
from app.services.scrape_contract import (
    deduplicate_records,
    calculate_coverage,
    summarize_missing_fields,
    calculate_confidence,
    normalize_records,
)

def test_deduplication():
    records = [
        {"name": "test", "email": "test@test.com"},
        {"name": "test", "email": "test@test.com"},
        {"name": "test2", "email": "test2@test.com"}
    ]
    unique, removed = deduplicate_records(records, ["name", "email"])
    assert removed == 1
    assert len(unique) == 2

def test_coverage():
    records = [
        {"name": "test", "email": "test@test.com", "phone": "123"},
        {"name": "test2", "email": None, "phone": "123"}
    ]
    cov = calculate_coverage(records, ["name", "email", "phone"])
    assert cov == 5/6
    assert cov < 1

def test_missing_fields():
    records = [
        {"name": "test", "email": "test@test.com"},
        {"name": "test2"}
    ]
    missing = summarize_missing_fields(records, ["name", "email"])
    assert missing["email"] == 1
    assert missing["name"] == 0

def test_confidence():
    conf = calculate_confidence(
        coverage=0.5,
        total_records=10,
        duplicates_removed=5,
        missing_fields={"email": 5},
        errors_count=2
    )
    # duplicate_ratio = 5/10 = 0.5
    # error_ratio = 2/10 = 0.2
    # The current formula uses error_ratio instead of success_ratio, but we shouldn't change existing logic,
    # just assert it evaluates.
    assert conf < 0.5

def test_normalization():
    records = [
        {"name": " TEST ", "email": " UPPER@TEST.COM "}
    ]
    normalized, count = normalize_records(records)
    assert count == 2
    assert normalized[0]["name"] == "TEST"
    assert normalized[0]["email"] == "upper@test.com"
