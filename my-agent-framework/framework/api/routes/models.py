"""Model management endpoints"""
from fastapi import APIRouter, Request

router = APIRouter(tags=["models"])


@router.get("/models")
async def list_models(request: Request):
    """Daftar model yang tersedia di Ollama."""
    mm = getattr(request.app.state, "model_manager", None)
    if mm is None:
        return {"models": [], "default": None}

    try:
        default = mm._default_adapter
        default_name = default.model_name if default and hasattr(default, "model_name") else None

        # Coba ambil list model dari Ollama adapter
        if default and hasattr(default, "get_available_models"):
            available = default.get_available_models(use_cache=True)
        else:
            available = [default_name] if default_name else []

        return {"models": available, "default": default_name}
    except Exception as e:
        return {"models": [], "default": None, "error": str(e)}


@router.get("/models/health")
async def models_health(request: Request):
    """Health check semua adapter yang terdaftar."""
    mm = getattr(request.app.state, "model_manager", None)
    if mm is None:
        return {"status": "no model manager"}
    try:
        return {"status": "ok", "adapters": mm.check_all_health()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
