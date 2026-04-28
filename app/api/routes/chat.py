import logging

from fastapi import APIRouter, HTTPException, status
from app.api.schemas.chat_schema import ChatRequest
from app.api.schemas.response_schema import ChatResponse
from app.core.rag_engine import answer_question, _format_source_attribution

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        # Get answer and source metadata
        answer, source_meta = answer_question(request.question, return_source=True)
    except RuntimeError as exc:
        error_text = str(exc)
        logger.warning("Chat request failed due to upstream LLM error: %s", error_text)

        lowered = error_text.lower()
        if "429" in error_text or "too many requests" in lowered or "rate" in lowered:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="LLM provider rate limit reached. Please retry shortly or use a different API key/project.",
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider is temporarily unavailable. Please try again.",
        )

    # Format source attribution string
    source_str = _format_source_attribution(source_meta)
    
    # Append source to answer if available
    if source_str:
        final_answer = answer + source_str
    else:
        final_answer = answer
    
    return ChatResponse(
        answer=final_answer,
        source=source_str.strip() if source_str else None
    )