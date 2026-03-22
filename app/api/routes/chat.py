from fastapi import APIRouter
from app.api.schemas.chat_schema import ChatRequest
from app.api.schemas.response_schema import ChatResponse
from app.core.rag_engine import answer_question, _format_source_attribution

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    
    # Get answer and source metadata
    answer, source_meta = answer_question(request.question, return_source=True)

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