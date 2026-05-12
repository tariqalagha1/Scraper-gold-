from typing import Any, Dict

SOURCE_RELIABILITY: Dict[str, Dict[str, Any]] = {}

def _calculate_score(profile: Dict[str, Any]) -> float:
    total = profile.get("total_runs", 0)
    if total == 0:
        return 0.0
        
    success_runs = profile.get("success_runs", 0)
    success_rate = success_runs / total
    
    avg_conf = profile.get("average_confidence", 0.0)
    avg_cov = profile.get("average_coverage", 0.0)
    avg_lat = profile.get("average_latency_ms", 0.0)
    
    latency_score = max(0.0, 1.0 - (avg_lat / 30000.0))
    
    score = (success_rate * 0.4) + (avg_conf * 0.3) + (avg_cov * 0.2) + (latency_score * 0.1)
    return max(0.0, min(1.0, score))

def record_source_result(
    source: str,
    status: str,
    total: int,
    coverage: float,
    confidence: float,
    latency_ms: float,
    duplicates_removed: int
) -> None:
    if source not in SOURCE_RELIABILITY:
        SOURCE_RELIABILITY[source] = {
            "source": source,
            "total_runs": 0,
            "success_runs": 0,
            "failed_runs": 0,
            "empty_runs": 0,
            "average_coverage": 0.0,
            "average_confidence": 0.0,
            "average_latency_ms": 0.0,
            "duplicates_rate": 0.0,
            "last_status": "failed",
            "reliability_score": 0.0
        }
        
    profile = SOURCE_RELIABILITY[source]
    
    # Update counts
    profile["total_runs"] += 1
    
    is_success = status in ("success", "completed", "partial")
    
    if is_success and total > 0:
        profile["success_runs"] += 1
    elif is_success and total == 0:
        profile["empty_runs"] += 1
        # It's an empty run, treat as failed for success rate? The prompt distinguishes empty_runs and failed_runs.
        # Let's count empty_runs as not successful for success_runs
    else:
        profile["failed_runs"] += 1
        
    profile["last_status"] = "success" if is_success and total > 0 else "failed"
    
    # Rolling averages
    n = profile["total_runs"]
    profile["average_coverage"] = ((profile["average_coverage"] * (n - 1)) + coverage) / n
    profile["average_confidence"] = ((profile["average_confidence"] * (n - 1)) + confidence) / n
    profile["average_latency_ms"] = ((profile["average_latency_ms"] * (n - 1)) + latency_ms) / n
    
    # Duplicates rate (duplicates_removed / total_extracted)
    total_extracted = total + duplicates_removed
    current_dup_rate = (duplicates_removed / total_extracted) if total_extracted > 0 else 0.0
    profile["duplicates_rate"] = ((profile["duplicates_rate"] * (n - 1)) + current_dup_rate) / n
    
    profile["reliability_score"] = _calculate_score(profile)

def get_all_reliability_profiles() -> Dict[str, Dict[str, Any]]:
    return SOURCE_RELIABILITY

def get_reliability_score(source: str) -> float:
    profile = SOURCE_RELIABILITY.get(source)
    if not profile:
        return 0.0
    return profile.get("reliability_score", 0.0)
