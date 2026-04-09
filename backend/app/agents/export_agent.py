from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.export.excel import ExcelExporter
from app.export.pdf import PDFExporter
from app.export.word import WordExporter


class ExportAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_name="export_agent")
        self.excel_exporter = ExcelExporter()
        self.pdf_exporter = PDFExporter()
        self.word_exporter = WordExporter()

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        processed = self._resolve_processed_payload(input_data)
        if not isinstance(processed, dict):
            return self._failure_payload("Input must include processed JSON from the Processing Agent.")

        if processed.get("status") in {"success", "fail"}:
            if processed.get("status") != "success":
                return self._failure_payload(processed.get("error", "Processed payload is not successful."))
            processed_data = processed.get("data", {})
            processed_metadata = processed.get("metadata", {}) if isinstance(processed.get("metadata"), dict) else {}
        else:
            processed_data = processed
            processed_metadata = {}

        if not isinstance(processed_data, dict):
            return self._failure_payload("Processed data must be an object.")

        source_url = str(input_data.get("source_url") or processed_metadata.get("source_url") or "")
        export_id = str(input_data.get("export_id") or "")
        generated_at = datetime.now(timezone.utc).isoformat()
        title = input_data.get("title") or "Processed Web Data Export"
        analysis_data = input_data.get("analysis")

        excel_path = await self.excel_exporter.export(
            processed_data,
            analysis_data=analysis_data,
            export_id=export_id or None,
            source_url=source_url,
            generated_at=generated_at,
            title=title,
        )
        pdf_path = await self.pdf_exporter.export(
            processed_data,
            analysis_data=analysis_data,
            export_id=export_id or None,
            source_url=source_url,
            generated_at=generated_at,
            title=title,
        )
        word_path = await self.word_exporter.export(
            processed_data,
            analysis_data=analysis_data,
            export_id=export_id or None,
            source_url=source_url,
            generated_at=generated_at,
            title=title,
        )

        return {
            "status": "success",
            "data": {
                "excel_path": excel_path,
                "pdf_path": pdf_path,
                "word_path": word_path,
                "analysis_included": bool(analysis_data),
                "requested_export_id": export_id or None,
            },
            "error": None,
            "metadata": {
                "agent": self.agent_name,
                "timestamp": generated_at,
                "source": source_url,
            },
        }

    def _resolve_processed_payload(self, input_data: dict[str, Any]) -> Any:
        if "processed" in input_data:
            return input_data["processed"]
        return input_data

    def _failure_payload(self, error: str) -> dict[str, Any]:
        return {
            "status": "fail",
            "data": {
                "excel_path": "",
                "pdf_path": "",
                "word_path": "",
            },
            "error": error,
            "metadata": {
                "agent": self.agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
