"""File upload endpoint"""
from fastapi import APIRouter, UploadFile, File
router = APIRouter(tags=["upload"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload file ke knowledge base."""
    content = await file.read()
    return {"filename": file.filename, "size": len(content), "status": "uploaded"}
