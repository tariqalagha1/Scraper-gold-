import json
import logging
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class JobCheckpoint(BaseModel):
    run_id: str
    status: str
    current_page: int
    collected_count: int
    retry_count: int
    failed_pages: List[str]
    partial_results_path: str

class AsyncRecoveryManager:
    """Manages async execution state, resumable jobs, and checkpoint persistence."""
    
    def __init__(self, storage_dir: str = "/tmp/scraper_checkpoints"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        
    def _get_checkpoint_path(self, run_id: str) -> str:
        return os.path.join(self.storage_dir, f"{run_id}_checkpoint.json")
        
    def save_checkpoint(self, checkpoint: JobCheckpoint):
        """Persist workflow state to survive timeouts."""
        path = self._get_checkpoint_path(checkpoint.run_id)
        with open(path, 'w') as f:
            f.write(checkpoint.model_dump_json(indent=2))
        logger.info(f"Checkpoint saved for run {checkpoint.run_id}. Collected: {checkpoint.collected_count}")

    def load_checkpoint(self, run_id: str) -> Optional[JobCheckpoint]:
        """Load checkpoint to resume execution after transient failure."""
        path = self._get_checkpoint_path(run_id)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                return JobCheckpoint(**data)
        return None

    def record_page_failure(self, run_id: str, page_url: str):
        """Track failed pages without terminating the entire workflow."""
        ckpt = self.load_checkpoint(run_id)
        if ckpt:
            ckpt.failed_pages.append(page_url)
            self.save_checkpoint(ckpt)
            
    def append_partial_results(self, run_id: str, new_records: List[Dict[str, Any]]):
        """Incremental save of records to prevent data loss on timeout."""
        ckpt = self.load_checkpoint(run_id)
        if not ckpt:
            return
            
        results_path = ckpt.partial_results_path
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        
        existing = []
        if os.path.exists(results_path):
            with open(results_path, 'r') as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    pass
                    
        existing.extend(new_records)
        
        with open(results_path, 'w') as f:
            json.dump(existing, f)
            
        ckpt.collected_count = len(existing)
        self.save_checkpoint(ckpt)
