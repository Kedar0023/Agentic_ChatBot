from app.models.document import DocumentStatus
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.repositories.thread_repo import ThreadRepo, DocumentRepo
from app.schema.authSchema import TokenPayload


# Local S3 bucket root — mirrors the Cloudflare R2 key layout.
# In production, swap this with boto3 / S3-compatible client calls.
# ---------------------------------------------------------------------------
S3_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "s3"

# Max upload size: 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}


# ---------------------------------------------------------------------------
#     Key layout:  s3/<user_id>/<thread_id>/<doc_id>/<original_filename>
async def upload_document_controller(
    thread_id: str,
    access_token: TokenPayload,
    db: Session,
    file: UploadFile,
):
    user_id = int(access_token.sub)

    thread = ThreadRepo.get_by_id_and_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Thread not found or access denied.")

    # Validate file and content type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. "
            f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    # Read file contents into memory (bounded by MAX_FILE_SIZE_BYTES)
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    doc_id = uuid.uuid4()
    # Key mirrors R2 bucket structure:  <user_id>/<thread_id>/<doc_id>/<filename>
    s3_key = f"{user_id}/{thread_id}/{doc_id}/{file.filename}"
    dest_path = S3_ROOT / s3_key

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(file_bytes)
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist file to storage: {e}",
        )

    document = DocumentRepo.create(
        db,
        thread_id=thread.id,
        filename=file.filename,
        s3_key=s3_key,
        content_type=content_type,
        file_size_bytes=file_size,
        status=DocumentStatus.PENDING,
    )

    try:
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        # Clean up the written file on DB failure
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to save document record. Please try again.",
        )

    return {
        "message": "Document uploaded successfully.",
        "document": {
            "id": str(document.id),
            "thread_id": str(document.thread_id),
            "filename": document.filename,
            "s3_key": document.s3_key,
            "content_type": document.content_type,
            "file_size_bytes": document.file_size_bytes,
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
        },
    }


# ---------------------------------------------------------------------------
#     GET  /chat/{thread_id}/documents/{document_id}
#     Returns the file from local S3 storage as a downloadable response.
# ---------------------------------------------------------------------------
async def get_document_controller(
    thread_id: str,
    document_id: str,
    access_token: TokenPayload,
    db: Session,
):
    user_id = int(access_token.sub)

    # 1. Verify the thread belongs to this user
    thread = ThreadRepo.get_by_id_and_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Thread not found or access denied.")

    # 2. Fetch the document and ensure it belongs to this thread
    document = DocumentRepo.get_by_id_and_thread(db, document_id, thread_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 3. Resolve file on local disk
    file_path = S3_ROOT / document.s3_key
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found in storage. It may have been deleted.",
        )

    # 4. Stream the file back to the client
    return FileResponse(
        path=str(file_path),
        media_type=document.content_type or "application/octet-stream",
        filename=document.filename,
    )
