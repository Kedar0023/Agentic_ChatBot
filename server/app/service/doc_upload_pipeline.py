from app.schema.authSchema import TokenPayload
from sqlalchemy.orm import Session
from fastapi import File, UploadFile

async def upload_document_controller(
    thread_id: str,
    access_token: TokenPayload,
    db: Session,
    file: UploadFile,
):
    
    # save doc in  /home/kedar/me/Agentic AI/TheChatBot/s3
    
    # save doc record in db with status=processing
    # pass doc to lc workflow
    # split text
    # embed text
    # store embeddings in vector db

    # /home/kedar/me/Agentic AI/TheChatBot/server

    return {"message": "Document uploaded successfully."}