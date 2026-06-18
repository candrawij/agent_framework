"""
auth.py — JWT Authentication Middleware
"""
from fastapi import Request, HTTPException
from framework.security.jwt_handler import JWTHandler

_jwt = JWTHandler()

async def auth_middleware(request: Request, call_next):
    """Verifikasi JWT token dari header Authorization."""
    public_paths = ["/health", "/api/docs", "/api/redoc", "/openapi.json"]
    if any(request.url.path.startswith(p) for p in public_paths):
        return await call_next(request)
    
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token:
        payload = _jwt.verify(token)
        if payload:
            request.state.user = payload
            return await call_next(request)
    
    # Untuk development: izinkan semua (hapus di production)
    return await call_next(request)
