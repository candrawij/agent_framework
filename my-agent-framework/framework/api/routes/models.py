"""Model management endpoints"""
from fastapi import APIRouter
router = APIRouter(tags=["models"])

@router.get("/models")
async def list_models():
    """Daftar model yang tersedia."""
    # TODO: Inject ModelManager dari app state
    return {"models": [], "default": None}

@router.get("/models/health")
async def models_health():
    return {}
