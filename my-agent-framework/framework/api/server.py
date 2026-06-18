"""
server.py — FastAPI Application Entry Point

Menyambungkan ModelManager dan AgentLoop ke app.state
sehingga route /chat bisa menggunakannya secara real.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import chat, agents, sessions, models, upload
from .websocket import router as ws_router
from .middleware import setup_middleware

logger = logging.getLogger("framework.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — setup saat startup, cleanup saat shutdown.
    """
    logger.info("Framework API starting up...")

    # ===== Setup ModelManager =====
    try:
        from model_layer.model_manager import ModelManager

        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        fast_model = os.getenv("FAST_MODEL", "qwen2.5:3b")
        reasoning_model = os.getenv("REASONING_MODEL", "qwen3:4b")

        model_manager = ModelManager.with_ollama(
            fast_model=fast_model,
            reasoning_model=reasoning_model,
            base_url=ollama_url,
        )
        app.state.model_manager = model_manager
        logger.info(f"ModelManager ready: {fast_model} @ {ollama_url}")
    except Exception as e:
        logger.warning(f"ModelManager setup failed (Ollama mungkin belum berjalan): {e}")
        app.state.model_manager = None

    # ===== Setup AgentLoop (opsional) =====
    try:
        from framework.loop.agent_loop import AgentLoop
        app.state.agent_loop = None
        if app.state.model_manager:
            agent_loop = AgentLoop(
                model_manager=app.state.model_manager,
                max_iterations=10
            )
            app.state.agent_loop = agent_loop
            logger.info("AgentLoop ready with ModelManager")
        else:
            logger.warning("AgentLoop cannot start: ModelManager is not available")
    except Exception as e:
        logger.warning(f"AgentLoop setup failed: {e}")
        app.state.agent_loop = None

    logger.info("Framework API ready. Docs: http://localhost:8000/api/docs")
    yield

    # ===== Shutdown =====
    logger.info("Framework API shutting down...")


# ===== App =====

def create_app() -> FastAPI:
    """Factory function untuk membuat app — memudahkan testing."""
    app = FastAPI(
        title="Agent Framework API",
        description=(
            "Custom Multi-Agent Framework REST API\n\n"
            "## Quick Start\n"
            "1. Pastikan Ollama berjalan: `ollama serve`\n"
            "2. Pull model: `ollama pull qwen2.5:3b`\n"
            "3. POST ke `/api/v1/chat` dengan body `{messages: [{role: 'user', content: 'Halo!'}]}`\n"
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # CORS — izinkan gateway desktop dan mobile
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,capacitor://localhost").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Ganti dengan cors_origins di production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")
    app.include_router(models.router, prefix="/api/v1")
    app.include_router(upload.router, prefix="/api/v1")
    app.include_router(ws_router, prefix="/ws")

    setup_middleware(app)

    @app.get("/health", tags=["system"])
    async def health_check():
        """Health check endpoint — cek apakah model tersambung."""
        model_ok = False
        model_name = "none"
        if hasattr(app.state, "model_manager") and app.state.model_manager:
            try:
                mm = app.state.model_manager
                # Ambil model_name dari default adapter
                default = mm._default_adapter
                if default and hasattr(default, "model_name"):
                    model_name = default.model_name
                    model_ok = True
                else:
                    stats = mm.get_stats()
                    model_name = stats.get("default", "configured")
                    model_ok = True
            except Exception:
                pass
        return {
            "status": "ok",
            "version": "1.0.0",
            "model_connected": model_ok,
            "model": model_name,
        }


    return app


app = create_app()


def main():
    """Entry point untuk `framework-server` CLI."""
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn.run(
        "framework.api.server:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
