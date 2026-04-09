"""Agent package exports.

Imports are intentionally lazy so optional runtime dependencies used by one
agent do not break unrelated parts of the pipeline.
"""

__all__ = [
    "BaseAgent",
    "IntakeAgent",
    "ScraperAgent",
    "ProcessingAgent",
    "VectorAgent",
    "AnalysisAgent",
    "ExportAgent",
]


def __getattr__(name: str):
    if name == "BaseAgent":
        from app.agents.base_agent import BaseAgent

        return BaseAgent
    if name == "IntakeAgent":
        from app.agents.intake_agent import IntakeAgent

        return IntakeAgent
    if name == "ScraperAgent":
        from app.agents.scraper_agent import ScraperAgent

        return ScraperAgent
    if name == "ProcessingAgent":
        from app.agents.processing_agent import ProcessingAgent

        return ProcessingAgent
    if name == "VectorAgent":
        from app.agents.vector_agent import VectorAgent

        return VectorAgent
    if name == "AnalysisAgent":
        from app.agents.analysis_agent import AnalysisAgent

        return AnalysisAgent
    if name == "ExportAgent":
        from app.agents.export_agent import ExportAgent

        return ExportAgent
    raise AttributeError(name)
