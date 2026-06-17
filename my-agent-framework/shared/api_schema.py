"""
api_schema.py — Pydantic Models untuk API (shared Python side)
"""
from pydantic import BaseModel
from typing import List, Literal, Optional


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
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


class AgentInfo(BaseModel):
    name: str
    description: str
    enabled: bool
    tools: List[str] = []


class HealthResponse(BaseModel):
    status: str
    version: str
