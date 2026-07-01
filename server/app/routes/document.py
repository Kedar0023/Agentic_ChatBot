# POST/api/threads/{thread_id}/documents
# GET/api/threads/{thread_id}/documents/{document_id}/status
# GET/api/threads/{thread_id}/documents
# DELETE/api/threads/{thread_id}/documents/{document_id}
# POST/api/threads/{thread_id}/documents/{document_id}/reprocess

from fastapi import APIRouter, Depends , File, UploadFile

from app.core.middleware import authenticate_user
from app.database.db import get_db
from app.schema.authSchema import TokenPayload
from typing import Annotated
from sqlalchemy.orm import Session
from app.service import document

router = APIRouter(prefix="/chat/{thread_id}")

# ---------------------------------------------------------------------------

@router.post("/documents", status_code=201)
async def upload_document(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    return await document.upload_document_controller(thread_id, access_token, db, file)
