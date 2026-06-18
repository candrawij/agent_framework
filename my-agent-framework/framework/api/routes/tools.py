"""
tools.py — Tool Management Endpoints

GET /api/v1/tools       — list semua tool yang terdaftar
GET /api/v1/tools/{name} — detail satu tool
POST /api/v1/tools/{name}/execute — eksekusi tool langsung (untuk testing)
GET /api/v1/tools/log   — log eksekusi terakhir
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Dict, Optional

router = APIRouter(tags=["tools"])


def _get_registry(request: Request):
    return getattr(request.app.state, "tool_registry", None)


@router.get("/tools")
async def list_tools(request: Request):
    """Daftar semua tool yang terdaftar."""
    registry = _get_registry(request)
    if registry is None:
        return {"tools": [], "total": 0, "message": "ToolRegistry belum diinisialisasi"}

    return {
        "tools": registry.get_info_list(),
        "total": len(registry),
        "enabled": registry.get_stats()["enabled"],
    }


@router.get("/tools/log")
async def get_tool_log(request: Request, last_n: int = 20):
    """Log eksekusi tool terakhir."""
    registry = _get_registry(request)
    if registry is None:
        return {"log": []}
    return {"log": registry.get_execution_log(last_n)}


@router.get("/tools/{name}")
async def get_tool(name: str, request: Request):
    """Detail satu tool berdasarkan nama."""
    registry = _get_registry(request)
    if registry is None:
        raise HTTPException(status_code=503, detail="ToolRegistry tidak tersedia")

    tool = registry._tools.get(name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' tidak ditemukan")

    return {
        **tool.get_info(),
        "schema": tool.get_schema(),
        "enabled": name not in registry._disabled,
    }


class ExecuteToolRequest(BaseModel):
    arguments: Dict[str, Any] = {}


@router.post("/tools/{name}/execute")
async def execute_tool(name: str, body: ExecuteToolRequest, request: Request):
    """
    Eksekusi tool langsung untuk testing.
    Tidak melalui AgentLoop — langsung panggil tool.
    """
    registry = _get_registry(request)
    if registry is None:
        raise HTTPException(status_code=503, detail="ToolRegistry tidak tersedia")

    result = registry.execute(name, body.arguments)
    if not result["success"] and result.get("error", "").startswith("Tool"):
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.patch("/tools/{name}/toggle")
async def toggle_tool(name: str, request: Request, enable: bool = True):
    """Enable atau disable tool tanpa restart."""
    registry = _get_registry(request)
    if registry is None:
        raise HTTPException(status_code=503, detail="ToolRegistry tidak tersedia")

    if name not in registry:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' tidak ditemukan")

    if enable:
        registry.enable(name)
    else:
        registry.disable(name)

    return {"tool": name, "enabled": enable, "message": f"Tool '{name}' {'diaktifkan' if enable else 'dinonaktifkan'}"}
