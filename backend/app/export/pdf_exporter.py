from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.export.base_exporter import BaseExporter
from app.export.contract_helpers import (
    get_export_data,
    get_export_errors,
    get_export_execution_summary,
    get_export_metadata,
    normalize_export_contract,
)


class PDFExporter(BaseExporter):
    async def export(
        self,
        processed_data: dict[str, Any],
        *,
        analysis_data: dict[str, Any] | None = None,
        export_id: str | None = None,
        source_url: str = "",
        generated_at: str | None = None,
        title: str = "",
    ) -> str:
        resolved_export_id = self.resolve_export_id(export_id)
        resolved_generated_at = self.resolve_generated_at(generated_at)
        contract = normalize_export_contract(processed_data, analysis_data=analysis_data, source_url=source_url)
        metadata = get_export_metadata(contract)
        execution = get_export_execution_summary(contract)
        records = get_export_data(contract)
        errors = get_export_errors(contract)

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=48,
            leftMargin=48,
            topMargin=48,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()
        story: list[Any] = []

        story.append(Paragraph(title or "Extraction Report", styles["Title"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"<b>Source:</b> {metadata['URL']}", styles["Normal"]))
        story.append(Paragraph(f"<b>Status:</b> {contract.get('status', '')}", styles["Normal"]))
        story.append(Paragraph(f"<b>Run ID:</b> {metadata['Run ID']}", styles["Normal"]))
        story.append(Paragraph(f"<b>Date:</b> {resolved_generated_at}", styles["Normal"]))
        story.append(Spacer(1, 0.18 * inch))

        story.append(Paragraph("<b>Summary</b>", styles["Heading2"]))
        story.append(Paragraph(f"Items extracted: {len(records)}", styles["BodyText"]))
        story.append(Paragraph(f"Validation result: {execution['Validation Status']}", styles["BodyText"]))
        story.append(Paragraph(f"Retry attempted: {execution['Retry Attempted']}", styles["BodyText"]))
        story.append(Paragraph(f"Memory used: {execution['Memory Used']}", styles["BodyText"]))
        story.append(Spacer(1, 0.18 * inch))

        story.append(Paragraph("<b>Decision</b>", styles["Heading2"]))
        story.append(Paragraph(f"Page Type: {execution['Page Type']}", styles["BodyText"]))
        story.append(Paragraph(f"Decision Confidence: {execution['Decision Confidence']}", styles["BodyText"]))
        story.append(Paragraph(execution["Decision Reason"] or "No decision reason available.", styles["BodyText"]))
        story.append(Spacer(1, 0.18 * inch))

        story.append(Paragraph("<b>Data Preview</b>", styles["Heading2"]))
        preview_rows = records[:10]
        if preview_rows:
            headers = sorted({key for row in preview_rows for key in row.keys()})[:5]
            table_rows = [headers] + [[str(row.get(header, "")) for header in headers] for row in preview_rows]
            pdf_table = Table(table_rows, repeatRows=1)
            pdf_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(pdf_table)
        else:
            story.append(Paragraph("No structured data available.", styles["BodyText"]))
        story.append(Spacer(1, 0.18 * inch))

        story.append(Paragraph("<b>Errors</b>", styles["Heading2"]))
        for error in errors:
            story.append(Paragraph(f"- {error}", styles["BodyText"]))

        document.build(story)
        return self.write_export_file("pdf", buffer.getvalue(), export_id=resolved_export_id)
