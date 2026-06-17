"""POST /api/v1/chat — Chat endpoint"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(tags=["chat"])

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

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Kirim pesan ke agent dan dapatkan response.
    TODO: Inject AgentLoop dan ModelManager dari app state.
    """
    import uuid
    session_id = request.session_id or str(uuid.uuid4())[:8]
    
    # TODO: Gunakan AgentLoop.run() untuk memproses pesan
    # Sementara: echo response
    last_msg = request.messages[-1].content if request.messages else ""
    return ChatResponse(
        content=f"[Framework] Echo: {last_msg}",
        session_id=session_id,
        model="stub",
        agent_used=request.agent_name,
    )
