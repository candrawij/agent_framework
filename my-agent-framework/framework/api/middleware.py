"""
middleware.py — Request/Response Middleware
"""
import time
import logging
from fastapi import FastAPI, Request

logger = logging.getLogger("framework.api")

def setup_middleware(app: FastAPI):
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration:.0f}ms)")
        return response
