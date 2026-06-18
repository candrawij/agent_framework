"""
chat.py — POST /api/v1/chat dan POST /api/v1/chat/stream

Diwire ke AgentLoop + ModelManager agar bukan stub lagi.
Success Criteria Sprint 1b: request ke endpoint ini harus menghasilkan
response nyata dari model (bukan echo/stub).
"""
import uuid
import asyncio
import json
import logging
from typing import AsyncIterator, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("framework.api.chat")
router = APIRouter(tags=["chat"])


# ===== Request / Response Models =====

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: Optional[str] = None
    stream: bool = False
    agent_name: Optional[str] = None
    temperature: float = 0.7


class ChatResponse(BaseModel):
    content: str
    session_id: str
    model: str
    agent_used: Optional[str] = None


# ===== Helpers =====

def _get_model_manager(request: Request):
    """Ambil ModelManager dari app state jika ada."""
    return getattr(request.app.state, "model_manager", None)


def _get_agent_loop(request: Request):
    """Ambil AgentLoop dari app state jika ada."""
    return getattr(request.app.state, "agent_loop", None)


def _build_messages(chat_messages: List[ChatMessage]) -> List[dict]:
    """Convert Pydantic messages ke format dict untuk adapters."""
    return [{"role": m.role, "content": m.content} for m in chat_messages]


# ===== Endpoints =====

@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """
    Kirim pesan ke agent dan dapatkan response penuh.

    Flow:
    - Jika AgentLoop tersedia di app.state → gunakan AgentLoop.run()
    - Jika hanya ModelManager tersedia → bypass loop, langsung ke model
    - Jika tidak ada keduanya → kembalikan error yang informatif
    """
    session_id = body.session_id or str(uuid.uuid4())[:8]
    messages = _build_messages(body.messages)
    last_user_msg = body.messages[-1].content if body.messages else ""

    # Coba gunakan AgentLoop
    agent_loop = _get_agent_loop(request)
    if agent_loop is not None:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: agent_loop.run(
                    goal=last_user_msg,
                    context={"session_id": session_id, "messages": messages},
                )
            )
            return ChatResponse(
                content=result.final_answer if hasattr(result, "final_answer") else str(result),
                session_id=session_id,
                model=getattr(result, "model_used", "agent_loop"),
                agent_used=body.agent_name or "default",
            )
        except Exception as e:
            logger.error(f"AgentLoop error: {e}", exc_info=True)
            # Fall through ke ModelManager

    # Coba gunakan ModelManager langsung (bypass loop)
    model_manager = _get_model_manager(request)
    if model_manager is not None:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model_manager.complete(
                    messages=messages,
                    temperature=body.temperature,
                )
            )
            return ChatResponse(
                content=result.get("content", ""),
                session_id=session_id,
                model=result.get("model", "unknown"),
                agent_used=body.agent_name,
            )
        except Exception as e:
            logger.error(f"ModelManager error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Model error: {str(e)}")

    # Fallback: tidak ada model tersambung
    logger.warning("No ModelManager or AgentLoop configured in app.state")
    raise HTTPException(
        status_code=503,
        detail=(
            "Framework tidak terhubung ke model. "
            "Pastikan Ollama berjalan di localhost:11434 dan app.state.model_manager dikonfigurasi. "
            "Lihat framework/api/server.py untuk cara setup."
        ),
    )


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest):
    """
    Streaming response via Server-Sent Events (SSE).

    Gunakan endpoint ini untuk streaming token per token.
    WebSocket lebih disarankan untuk real-time streaming — lihat /ws/chat/{session_id}.
    """
    session_id = body.session_id or str(uuid.uuid4())[:8]
    messages = _build_messages(body.messages)

    model_manager = _get_model_manager(request)
    if model_manager is None:
        async def error_stream():
            yield f"data: {json.dumps({'error': 'No model configured'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def token_generator() -> AsyncIterator[str]:
        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
        try:
            # Stream dari ModelManager
            buffer = []
            for token in model_manager.stream(messages=messages, temperature=body.temperature):
                buffer.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            # Kirim event selesai
            full_content = "".join(buffer)
            yield f"data: {json.dumps({'type': 'done', 'full_content': full_content, 'session_id': session_id})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")
