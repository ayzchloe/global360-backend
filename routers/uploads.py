import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from database import get_db
import models
import auth

router = APIRouter(tags=["uploads"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "webp", "gif", "svg",
    "mp4", "zip", "tar", "gz", "txt", "csv", "json", "docx", "pptx"
}
MAX_FILE_SIZE_MB = 50


def _save_file(file: UploadFile):
    filename = file.filename or "uploaded_file"
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Generate unique filename to prevent collisions
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"File exceeds maximum size of {MAX_FILE_SIZE_MB}MB")

    return {
        "filename": filename,
        "saved_filename": unique_name,
        "url": f"/static/uploads/{unique_name}",
        "content_type": file.content_type,
        "size_bytes": file_size,
    }


@router.post("/uploads/", status_code=201)
@router.post("/instructor/upload", status_code=201)
def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Required for 'Upload Content' on instructor and course management pages.
    """
    return _save_file(file)
