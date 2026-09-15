from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.core.context import WorkingContext
from app.router.intent_router import conversation_history, process_context
from app.router.schemas import ChatRequest, ProcessingResponse

chat_router = APIRouter()


@chat_router.post("/chat", response_model=ProcessingResponse)
async def process_chat(request: ChatRequest) -> ProcessingResponse:
    try:
        session_id = request.session_id or str(uuid4())
        context = WorkingContext(
            session_id=session_id,
            user_id=request.user_id,
            transcript=request.transcript.strip(),
            input_type=request.input_type,
            conversation_history=conversation_history(session_id),
        )
        return await process_context(context)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Unable to process the request") from error
