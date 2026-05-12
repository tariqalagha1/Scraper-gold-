import hashlib
import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ExecutionPlan(BaseModel):
    workspace_type: str
    sources: List[str]
    target_records: int
    required_fields: List[str]
    strict_extraction: bool

class ExecutionContext:
    def __init__(self, run_id: str, request_data: Dict[str, Any], origin: str = "backend"):
        self.run_id = run_id
        self.request_data = request_data
        self.origin = origin
        self.is_locked = False
        self.contract_hash = self._generate_hash()
        
    def _generate_hash(self) -> str:
        # Create a deterministic hash of the extraction contract
        contract_data = {
            "workspace_type": self.request_data.get("workspace_type", "url"),
            "sources": sorted(self.request_data.get("sources", ["web"])),
            "target_records": self.request_data.get("target_records", 50),
            "required_fields": sorted(self.request_data.get("required_fields", [])),
            "entity_type": self.request_data.get("entity_type", ""),
            "strict_extraction": self.request_data.get("strict_extraction", True)
        }
        encoded = json.dumps(contract_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
        
    def lock(self):
        """Lock the execution contract to prevent runtime source mutation."""
        self.is_locked = True
        logger.info(f"Execution contract locked. Hash: {self.contract_hash}")
        self._trace_contract()
        
    def _trace_contract(self):
        """Log complete orchestration trace (Contract Tracing)."""
        trace_data = {
            "run_id": self.run_id,
            "workspace_type": self.request_data.get("workspace_type", "url"),
            "selected_sources": self.request_data.get("sources", ["web"]),
            "contract_hash": self.contract_hash,
            "contract_origin": self.origin,
            "validated": True
        }
        # In a real system, this would go to a database or dedicated tracing service
        logger.info(f"CONTRACT_TRACE: {json.dumps(trace_data)}")
        
    def get_plan_preview(self) -> ExecutionPlan:
        """Generate visible execution plan preview."""
        return ExecutionPlan(
            workspace_type=self.request_data.get("workspace_type", "url"),
            sources=self.request_data.get("sources", ["web"]),
            target_records=self.request_data.get("target_records", 50),
            required_fields=self.request_data.get("required_fields", []),
            strict_extraction=self.request_data.get("strict_extraction", True)
        )

    def mutate_sources(self, new_sources: List[str]):
        """Attempt to change sources at runtime."""
        if self.is_locked:
            raise RuntimeError("Cannot mutate sources: Execution contract is locked.")
        self.request_data["sources"] = new_sources
        self.contract_hash = self._generate_hash() # Re-hash if changed before lock
