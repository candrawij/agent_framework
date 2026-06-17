"""GET /api/v1/agents — Agent management endpoints"""
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter(tags=["agents"])

@router.get("/agents", response_model=List[Dict])
async def list_agents():
    """Daftar semua agent yang terdaftar."""
    # TODO: Inject AgentRegistry dari app state
    return [{"name": "supervisor", "description": "Default supervisor", "enabled": True}]

@router.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Detail satu agent."""
    return {"name": agent_name, "status": "available"}

@router.post("/agents/{agent_name}/enable")
async def enable_agent(agent_name: str):
    """Enable agent."""
    return {"status": "enabled", "agent": agent_name}

@router.post("/agents/{agent_name}/disable")
async def disable_agent(agent_name: str):
    """Disable agent."""
    return {"status": "disabled", "agent": agent_name}
