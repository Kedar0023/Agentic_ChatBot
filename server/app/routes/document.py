# POST/api/threads/{thread_id}/documents
# GET/api/threads/{thread_id}/documents/{document_id}/status
# GET/api/threads/{thread_id}/documents
# DELETE/api/threads/{thread_id}/documents/{document_id}
# POST/api/threads/{thread_id}/documents/{document_id}/reprocess
# POST/api/threads/{thread_id}/documents/{document_id}/process

from fastapi import APIRouter, Depends , File, UploadFile

from app.core.middleware import authenticate_user
from app.database.db import get_db
from app.schema.authSchema import TokenPayload
from typing import Annotated
from sqlalchemy.orm import Session
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


@router.get("/documents/{document_id}",status_code=200)
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

# pdf = "/home/kedar/me/Agentic AI/TheChatBot/s3/1/021c9ca5-58c2-4409-8aa7-25e0387feb49/4df9dec6-55ee-46e1-b564-e2c5f29c6060/Book_chapter_final.pdf"

# from app.langchain.rag_workflow import RAGWorkflow
# @app.get("/testpdf")
# async def test_pdf():
#     docs = RAGWorkflow.load_pdf(pdf)
#     chunks = RAGWorkflow.split_into_chunks(docs)
#     embeddings = RAGWorkflow.embed_chunks(chunks)

#     return [
#         {
#             "chunk": i + 1,
#             "page": chunk.metadata.get("page", 0) + 1,
#             "length": len(chunk.page_content),
#             "embedding_dimension": len(embeddings[i]),
#             "embedding_preview": embeddings[i][:5],  # first 5 values
#             "content": chunk.page_content,
#         }
#         for i, chunk in enumerate(chunks)
    # ]