"""
server.py — FastAPI Application Entry Point

Entry point untuk API server framework.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import chat, agents, sessions, models, upload
from .websocket import router as ws_router
from .auth import auth_middleware
from .middleware import setup_middleware

app = FastAPI(
    title="Agent Framework API",
    description="Custom Agent Framework REST API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(ws_router, prefix="/ws")

setup_middleware(app)

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("framework.api.server:app", host="0.0.0.0", port=8000, reload=True)
