"""Session management endpoints"""
from fastapi import APIRouter
router = APIRouter(tags=["sessions"])

@router.get("/sessions")
async def list_sessions():
    return []

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    return {"deleted": session_id}
