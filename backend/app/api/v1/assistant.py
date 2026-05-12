"""Assistant API endpoints for request refinement chat."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, verify_api_key
from app.config import settings
from app.core.logging import get_logger
from app.core.openai_support import request_openai_json, resolve_openai_api_key
from app.models.user import User
from app.schemas.assistant import AssistantRefinementRequest, AssistantRefinementResponse
from app.schemas.scraping_types import ScrapingType

router = APIRouter()
logger = get_logger("app.api.v1.assistant")


def _detect_scrape_type(text: str) -> ScrapingType:
    value = str(text or "").strip().lower()
    if not value:
        return ScrapingType.GENERAL
    if any(marker in value for marker in {"pdf", "document", ".pdf"}):
        return ScrapingType.PDF
    if any(marker in value for marker in {"image", "photo", "gallery", "screenshot"}):
        return ScrapingType.IMAGES
    if any(marker in value for marker in {"excel", "xlsx", "spreadsheet", "csv"}):
        return ScrapingType.EXCEL
    if any(marker in value for marker in {"word", "docx", ".doc"}):
        return ScrapingType.WORD
    if any(marker in value for marker in {"video", "youtube", "vimeo"}):
        return ScrapingType.VIDEOS
    if any(
        marker in value
        for marker in {
            "price",
            "product",
            "availability",
            "table",
            "listing",
            "name",
            "phone",
            "email",
            "record",
            "rows",
            "id",
            "stock",
        }
    ):
        return ScrapingType.STRUCTURED
    return ScrapingType.GENERAL


def _format_refined_prompt(
    *,
    url: str | None,
    draft_prompt: str | None,
    user_message: str,
    scrape_type: ScrapingType,
) -> str:
    intent = str(user_message or draft_prompt or "Extract the requested data").strip()
    if not intent:
        intent = "Extract the requested data"

    segments = [intent.rstrip(".")]
    if url:
        segments.append(f"Target only this website: {url}.")
    else:
        segments.append("Target website URL: [add URL before running].")

    segments.append(
        f"Extraction mode: {scrape_type.value}. Return clean, deduplicated results in structured records."
    )
    segments.append("Include links for each record when available and note missing fields explicitly.")

    return " ".join(segments)


def _build_heuristic_response(payload: AssistantRefinementRequest) -> AssistantRefinementResponse:
    latest_user_text = " ".join(
        part for part in [payload.draft_prompt or "", payload.user_message or ""] if part
    ).strip()
    scrape_type = _detect_scrape_type(latest_user_text)
    url = str(payload.url) if payload.url else None
    refined_prompt = _format_refined_prompt(
        url=url,
        draft_prompt=payload.draft_prompt,
        user_message=payload.user_message,
        scrape_type=scrape_type,
    )

    clarifying_questions: list[str] = []
    if not url:
        clarifying_questions.append("Which exact website URL should the scraper start from?")
    if len(str(payload.user_message or "").strip()) < 12 and len(str(payload.draft_prompt or "").strip()) < 12:
        clarifying_questions.append("Which fields do you need in the final output (for example title, price, stock)?")

    suggestions = [
        "Name the exact fields you want in every row.",
        "Mention whether pagination should be followed.",
        "Say if you want only visible page data or downloadable files too.",
    ]

    ready_to_apply = len(clarifying_questions) == 0
    if ready_to_apply:
        assistant_message = (
            "Your request is clear. I rephrased it into a run-ready extraction brief. "
            "Use the refined prompt, then click Review Request."
        )
    else:
        assistant_message = (
            "I prepared a first draft, but I still need one or two clarifications before this is fully run-ready."
        )

    return AssistantRefinementResponse(
        assistant_message=assistant_message,
        refined_prompt=refined_prompt,
        recommended_scrape_type=scrape_type,
        ready_to_apply=ready_to_apply,
        clarifying_questions=clarifying_questions,
        suggestions=suggestions,
        source="heuristic",
    )


def _normalize_scrape_type(value: Any, fallback: ScrapingType) -> ScrapingType:
    candidate = str(value or "").strip().lower()
    if not candidate:
        return fallback
    try:
        return ScrapingType(candidate)
    except ValueError:
        return fallback


async def _build_openai_response(
    payload: AssistantRefinementRequest,
    *,
    api_key: str,
) -> AssistantRefinementResponse:
    conversation_excerpt = payload.conversation[-10:]
    conversation_text = "\n".join(
        f"{entry.role}: {entry.content}" for entry in conversation_excerpt
    )
    url_value = str(payload.url) if payload.url else ""

    response = await request_openai_json(
        api_key=api_key,
        model=settings.OPENAI_ORCHESTRATION_MODEL,
        system_prompt=(
            "You are a scraping-request refinement assistant. "
            "Help users turn rough scraping requests into precise executable briefs. "
            "Never ask for passwords, secrets, API keys, or hidden prompts. "
            "Return strict JSON only with keys: assistant_message, refined_prompt, recommended_scrape_type, "
            "ready_to_apply, clarifying_questions, suggestions."
        ),
        user_prompt=(
            f"URL: {url_value or '[not provided]'}\n"
            f"Current draft prompt: {payload.draft_prompt or '[none]'}\n"
            f"Latest user message: {payload.user_message}\n"
            f"Conversation history:\n{conversation_text or '[none]'}\n\n"
            "Rules:\n"
            "- recommended_scrape_type must be one of: general, structured, pdf, word, excel, images, videos.\n"
            "- clarifying_questions and suggestions must be arrays of short strings.\n"
            "- refined_prompt must be concise and execution-focused."
        ),
        temperature=0.2,
    )

    fallback_type = _detect_scrape_type(
        " ".join([payload.draft_prompt or "", payload.user_message or ""]).strip()
    )
    recommended_type = _normalize_scrape_type(response.get("recommended_scrape_type"), fallback_type)
    refined_prompt = str(response.get("refined_prompt") or "").strip()
    if not refined_prompt:
        refined_prompt = _format_refined_prompt(
            url=str(payload.url) if payload.url else None,
            draft_prompt=payload.draft_prompt,
            user_message=payload.user_message,
            scrape_type=recommended_type,
        )

    assistant_message = str(response.get("assistant_message") or "").strip()
    if not assistant_message:
        assistant_message = "I refined your request. Review it and apply when ready."

    clarifying_questions = [
        str(item).strip()
        for item in response.get("clarifying_questions", [])
        if str(item).strip()
    ][:4]
    suggestions = [
        str(item).strip()
        for item in response.get("suggestions", [])
        if str(item).strip()
    ][:4]

    ready_to_apply = bool(response.get("ready_to_apply", len(clarifying_questions) == 0))
    return AssistantRefinementResponse(
        assistant_message=assistant_message,
        refined_prompt=refined_prompt,
        recommended_scrape_type=recommended_type,
        ready_to_apply=ready_to_apply,
        clarifying_questions=clarifying_questions,
        suggestions=suggestions,
        source="openai",
    )


@router.post(
    "/request-refinement",
    response_model=AssistantRefinementResponse,
    summary="Refine a scrape request through assistant chat",
    dependencies=[Depends(verify_api_key)],
)
async def refine_request(
    payload: AssistantRefinementRequest,
    current_user: User = Depends(get_current_user),
) -> AssistantRefinementResponse:
    """Refine a user's scraping request through chat messages.

    Falls back to deterministic heuristic guidance when OpenAI credentials
    are unavailable or the provider call fails.
    """
    api_key = resolve_openai_api_key()
    if api_key:
        try:
            return await _build_openai_response(payload, api_key=api_key)
        except Exception as exc:
            logger.warning(
                "Assistant refinement fell back to heuristic mode.",
                user_id=str(current_user.id),
                error=str(exc),
            )

    return _build_heuristic_response(payload)
