"""
chat.py — POST /api/v1/chat dan POST /api/v1/chat/stream

Sprint 7 upgrade:
- Non-stream: kembalikan tool_trace jika ada tool yang dipanggil
- Stream: tool events via SSE sebelum token respons final
"""
import asyncio
import json
import logging
import uuid
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
    tool_trace: Optional[list] = None  # Sprint 7: list tool calls yang dieksekusi


# ===== Helpers =====

def _get_model_manager(request: Request):
    return getattr(request.app.state, "model_manager", None)


def _get_agent_loop(request: Request):
    return getattr(request.app.state, "agent_loop", None)


def _get_tool_registry(request: Request):
    return getattr(request.app.state, "tool_registry", None)


def _build_messages(chat_messages: List[ChatMessage]) -> List[dict]:
    return [{"role": m.role, "content": m.content} for m in chat_messages]


# ===== Non-Streaming Chat =====

@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """
    Kirim pesan ke agent dan dapatkan response penuh.

    Flow:
    - AgentLoop.run() dengan ReAct tool calling (Sprint 7)
    - Fallback ke ModelManager langsung jika AgentLoop tidak ada
    """
    session_id = body.session_id or str(uuid.uuid4())[:8]
    messages = _build_messages(body.messages)
    last_user_msg = body.messages[-1].content if body.messages else ""

    # Gunakan AgentLoop (termasuk tool calling ReAct)
    agent_loop = _get_agent_loop(request)
    if agent_loop is not None:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: agent_loop.run(
                    goal=last_user_msg,
                    context={
                        "session_id": session_id,
                        "messages": messages,
                        "temperature": body.temperature,
                    },
                )
            )
            return ChatResponse(
                content=result.final_answer if hasattr(result, "final_answer") else str(result),
                session_id=session_id,
                model=getattr(result, "model_used", "agent_loop"),
                agent_used=body.agent_name or "default",
                tool_trace=getattr(result, "tool_trace", None),
            )
        except Exception as e:
            logger.error(f"AgentLoop error: {e}", exc_info=True)
            # Fall through ke ModelManager

    # Fallback: ModelManager langsung (bypass AgentLoop)
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

    raise HTTPException(
        status_code=503,
        detail=(
            "Framework tidak terhubung ke model. "
            "Pastikan Ollama berjalan di localhost:11434."
        ),
    )


# ===== Streaming Chat dengan Tool Events =====

@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest):
    """
    Streaming response via Server-Sent Events (SSE).

    Sprint 7 upgrade: Sebelum token respons, kirim tool_call events
    jika AgentLoop mengeksekusi tool selama proses.

    Event format:
    - {"type": "start", "session_id": "..."}
    - {"type": "tool_call", "tool": "...", "arguments": {...}, "result": "...", "success": bool}
    - {"type": "token", "content": "..."}
    - {"type": "done", "full_content": "...", "session_id": "...", "tool_trace": [...]}
    - {"type": "error", "message": "..."}
    """
    session_id = body.session_id or str(uuid.uuid4())[:8]
    messages = _build_messages(body.messages)
    last_user_msg = body.messages[-1].content if body.messages else ""

    model_manager = _get_model_manager(request)
    agent_loop = _get_agent_loop(request)

    if model_manager is None and agent_loop is None:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No model configured'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def token_generator() -> AsyncIterator[str]:
        yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
        try:
            tool_trace = []

            # Jika ada AgentLoop → gunakan ReAct loop (dengan tool calling)
            # Kita capture tool_trace dari result, lalu stream respons final
            if agent_loop is not None:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: agent_loop.run(
                        goal=last_user_msg,
                        context={
                            "session_id": session_id,
                            "messages": messages,
                            "temperature": body.temperature,
                        },
                    )
                )

                # Emit tool call events jika ada
                final_answer = result.final_answer if hasattr(result, "final_answer") else str(result)
                # Ambil tool_trace dari observations
                for obs in (result.observations or []):
                    if isinstance(obs, dict) and obs.get("source") == "tool_trace":
                        for trace in obs.get("data", []):
                            tool_trace.append(trace)
                            yield f"data: {json.dumps({'type': 'tool_call', **trace})}\n\n"

                # Stream final answer token per token
                for char in final_answer:
                    yield f"data: {json.dumps({'type': 'token', 'content': char})}\n\n"
                    await asyncio.sleep(0)  # allow event loop to breathe

                yield f"data: {json.dumps({'type': 'done', 'full_content': final_answer, 'session_id': session_id, 'tool_trace': tool_trace})}\n\n"

            else:
                # Fallback: stream langsung dari ModelManager
                buffer = []
                loop = asyncio.get_event_loop()

                def stream_sync():
                    return list(model_manager.stream(messages=messages, temperature=body.temperature))

                tokens = await loop.run_in_executor(None, stream_sync)
                for token in tokens:
                    buffer.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

                full_content = "".join(buffer)
                yield f"data: {json.dumps({'type': 'done', 'full_content': full_content, 'session_id': session_id})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
