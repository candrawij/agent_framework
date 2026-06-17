"""
websocket.py — WebSocket untuk Streaming Response
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()

@router.websocket("/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint untuk streaming chat."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # TODO: Gunakan AgentLoop.stream() untuk streaming
            await websocket.send_text(json.dumps({
                "type": "token",
                "content": f"[Stream] {msg.get('content', '')}",
                "session_id": session_id,
            }))
    except WebSocketDisconnect:
        pass
