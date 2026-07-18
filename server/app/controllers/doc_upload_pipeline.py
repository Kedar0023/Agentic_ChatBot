import uuid
from pathlib import Path

from app.services.cloudflare_r2 import delete_file, upload_file , get_downloadable_file
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.document import DocumentStatus
from app.repositories.thread_repo import DocumentRepo, ThreadRepo
from app.schema.authSchema import TokenPayload
from app.langchain.rag_workflow import RAGWorkflow
from app.vectorstores.chromadb import get_vector_store

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
# Key layout:  s3/<user_id>/<thread_id>/<doc_id>/<original_filename>
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

    s3_key = f"{user_id}/{thread_id}/{doc_id}/{file.filename}"
    try:
        upload_file(
            key=s3_key,
            file_bytes=file_bytes,
            content_type=content_type,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=500,
            detail="Failed to upload file.",
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
        delete_file(key=s3_key)              # Clean up the written file on DB failure
        raise HTTPException(
            status_code=500,
            detail="Failed to save document record. Please try again.",
        )

    return {
        "message": "Document uploaded successfully.",
    }

# ---------------------------------------------------------------------------
#     Returns the file from local S3 storage as a downloadable response.
async def get_document_controller(
    thread_id: str,
    document_id: str,
    access_token: TokenPayload,
    db: Session,
):
    user_id = int(access_token.sub)

    # Verify the thread belongs to this user
    thread = ThreadRepo.get_by_id_and_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Thread not found or access denied.")

    # Fetch the document and ensure it belongs to this thread
    document = DocumentRepo.get_by_id_and_thread(db, document_id, thread_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    res = get_downloadable_file(key=document.s3_key)

    return StreamingResponse(
        res["Body"],
        media_type=res.get("ContentType", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "Content-Length": str(res["ContentLength"]),
        },
    )


# ---------------------------------------------------------------------------
#     POST  /chat/{thread_id}/documents/{document_id}/process
#     Loads the PDF, splits into chunks, embeds, and stores in vector DB.
# ---------------------------------------------------------------------------
async def ingest_document(
    thread_id: str,
    document_id: str,
    access_token: TokenPayload,
    db: Session,
):
    user_id = int(access_token.sub)

    thread = ThreadRepo.get_by_id_and_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Thread not found or access denied.")

    # Fetch the doc (from Pg DB) and ensure it belongs to this thread
    doc = DocumentRepo.get_by_id_and_thread(db, document_id, thread_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    #NOTE: build a more generic pipeline for other file types in the future
    if doc.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF documents can be processed. Got: {doc.content_type}",
        )

    if doc.status == DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="Document has already been processed.",
        )

    res = get_downloadable_file(key=doc.s3_key)

    # Mark as PROCESSING
    doc.status = DocumentStatus.PROCESSING
    db.commit()
    db.refresh(doc)

    #  ingestion pipeline (load → split → embed → store in ChromaDB)
    try:
        pages = RAGWorkflow.load_pdf_from_bytes(res["Body"].read())
        chunks = RAGWorkflow.split_into_chunks(pages)
        if not chunks:
            raise ValueError("PDF produced zero chunks after splitting.")

        embeddings = RAGWorkflow.embed_chunks(chunks)

        # Prepare data for ChromaDB
        doc_id_str = str(doc.id)
        thread_id_str = str(doc.thread_id)

        chunk_ids = [f"{doc_id_str}__chunk_{i}" for i in range(len(chunks))]
        documents = [chunk.page_content for chunk in chunks]
        metadatas = [
            {
                "document_id": doc_id_str,
                "thread_id": thread_id_str,
                "filename": doc.filename,
                "page": chunk.metadata.get("page", 0),
                "chunk_index": i,
            }
            for i, chunk in enumerate(chunks)
        ]

        vector_store = get_vector_store()
        vector_store.add_documents(
            ids=chunk_ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        total_chunks = len(chunks)

    except Exception as e:
        doc.status = DocumentStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {e}",
        )

    # Mark as COMPLETED
    doc.status = DocumentStatus.COMPLETED
    db.commit()
    db.refresh(doc)

    return {
        "message": "Document processed successfully.",
        "document": {
            "id": str(doc.id),
            "thread_id": str(doc.thread_id),
            "filename": doc.filename,
            "status": doc.status.value,
            "total_chunks": total_chunks,
        },
    }
