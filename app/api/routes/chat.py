from fastapi import APIRouter
from app.api.schemas.chat_schema import ChatRequest
from app.api.schemas.response_schema import ChatResponse
from app.core.rag_engine import answer_question

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    answer = answer_question(request.question)

    return ChatResponse(answer=answer)