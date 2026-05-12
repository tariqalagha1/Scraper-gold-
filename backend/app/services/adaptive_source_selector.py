from typing import List
from dataclasses import dataclass
from app.services.source_reliability_service import get_reliability_score, SOURCE_RELIABILITY

DEFAULT_RELIABILITY = 0.5
MIN_RELIABILITY_THRESHOLD = 0.2

@dataclass
class ExecutionPlan:
    execution_order: List[str]
    sources_skipped: List[str]

def build_source_execution_plan(requested_sources: List[str], force_sources: bool = False) -> ExecutionPlan:
    if not requested_sources:
        return ExecutionPlan(execution_order=[], sources_skipped=[])
        
    scored_sources = []
    for source in requested_sources:
        if source in SOURCE_RELIABILITY:
            score = get_reliability_score(source)
        else:
            score = DEFAULT_RELIABILITY
        scored_sources.append((source, score))
        
    # Sort by reliability descending
    scored_sources.sort(key=lambda x: x[1], reverse=True)
    
    execution_order = []
    sources_skipped = []
    
    for source, score in scored_sources:
        if score < MIN_RELIABILITY_THRESHOLD and not force_sources:
            sources_skipped.append(source)
        else:
            execution_order.append(source)
            
    return ExecutionPlan(
        execution_order=execution_order,
        sources_skipped=sources_skipped
    )
