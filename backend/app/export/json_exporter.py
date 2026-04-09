from __future__ import annotations

from app.export.base_exporter import BaseExporter
from app.export.contract_helpers import get_export_json, normalize_export_contract


class JSONExporter(BaseExporter):
    async def export(
        self,
        processed_data,
        *,
        analysis_data=None,
        export_id=None,
        source_url="",
        generated_at=None,
        title="",
    ) -> str:
        contract = normalize_export_contract(processed_data, analysis_data=analysis_data, source_url=source_url)
        file_bytes = get_export_json(contract)
        return self.write_export_file("json", file_bytes, export_id=export_id)
