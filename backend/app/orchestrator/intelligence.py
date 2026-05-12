import re
from typing import Any, Dict, List

def calculate_entity_confidence(record: Dict[str, Any], required_fields: List[str], schema_fields: List[str]) -> Dict[str, float]:
    """
    Generate confidence scores for an extracted record:
    - confidence_score: Overall trust in the entity extraction.
    - schema_score: Completeness of requested schema.
    - source_quality_score: Heuristics based on page context.
    """
    # 1. Schema Completeness Score
    populated = sum(1 for f in schema_fields if record.get(f) and str(record.get(f)).strip())
    schema_score = (populated / len(schema_fields) * 100) if schema_fields else 0.0
    
    # 2. Required Fields Penalty
    missing_required = sum(1 for f in required_fields if not record.get(f) or not str(record.get(f)).strip())
    if missing_required > 0:
        schema_score *= 0.5  # Heavy penalty for missing required
        
    # 3. Source Quality Score (mock heuristics)
    source_url = str(record.get("source_url", "")).lower()
    source_quality_score = 50.0
    if "contact" in source_url or "about" in source_url or "profile" in source_url:
        source_quality_score = 90.0
    elif "article" in source_url or "blog" in source_url:
        source_quality_score = 30.0  # Generic articles get lower quality for entity extraction
        
    # 4. Overall Confidence
    confidence_score = (schema_score * 0.6) + (source_quality_score * 0.4)
    
    return {
        "confidence_score": round(confidence_score, 2),
        "schema_score": round(schema_score, 2),
        "source_quality_score": round(source_quality_score, 2)
    }

def rank_and_classify_page(html_content: str, url: str) -> Dict[str, Any]:
    """
    Before extraction, classify page type and entity relevance.
    Reject low-value pages.
    """
    url_lower = url.lower()
    content_lower = html_content.lower()[:5000] # Check first 5k chars
    
    page_type = "unknown"
    relevance_score = 50
    
    if "contact" in url_lower or "about" in url_lower:
        page_type = "contact_page"
        relevance_score = 95
    elif re.search(r"<(table|ul)[^>]*class=[\"'].*?(list|grid|directory).*?[\"']", content_lower):
        page_type = "structured_listing"
        relevance_score = 85
    elif "nav" in url_lower or "category" in url_lower:
        page_type = "navigation_page"
        relevance_score = 20
    elif "<article" in content_lower or "blog" in url_lower:
        page_type = "generic_article"
        relevance_score = 30
        
    extraction_feasible = relevance_score >= 40
    
    return {
        "page_type": page_type,
        "relevance_score": relevance_score,
        "extraction_feasible": extraction_feasible,
        "reason": "Relevance threshold met" if extraction_feasible else "Page classified as low-value"
    }
