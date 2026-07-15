# POST/api/threads/{thread_id}/documents
# GET/api/threads/{thread_id}/documents/{document_id}/status
# GET/api/threads/{thread_id}/documents
# DELETE/api/threads/{thread_id}/documents/{document_id}
# POST/api/threads/{thread_id}/documents/{document_id}/reprocess
# POST/api/threads/{thread_id}/documents/{document_id}/process

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.middleware import authenticate_user
from app.database.db import get_db
from app.schema.authSchema import TokenPayload
from app.service import doc_upload_pipeline as document

router = APIRouter(prefix="/chat/{thread_id}")

# ---------------------------------------------------------------------------


@router.post("/documents", status_code=201)
async def upload_document(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    # print(thread_id, access_token, db, file)
    return await document.upload_document_controller(thread_id, access_token, db, file)


@router.get("/documents/{document_id}", status_code=200)
async def get_document(
    thread_id: str,
    document_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await document.get_document_controller(thread_id, document_id, access_token, db)


@router.post("/documents/{document_id}/process", status_code=200)
async def process_document(
    thread_id: str,
    document_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await document.process_document_controller(thread_id, document_id, access_token, db)
