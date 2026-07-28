from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.controllers import chat
from app.core.middleware import authenticate_user
from app.database.db import get_async_db_session, get_db
from app.schema.authSchema import TokenPayload
from app.schema.chatSchema import ChatRequest, UpdateModelRequest, UpdateTitleRequest

router = APIRouter(prefix="/v1/chat")

# ---------------------------------------------------------------------------


# Stateless, unauthenticated chat with limited history.
@router.post("/free")
async def free_chat(req: ChatRequest):
    history = [entry.model_dump() for entry in req.history] if req.history else []

    if history and len(history) >= 20:
        raise HTTPException(status_code=400, detail="Free credits limit reached.")

    return StreamingResponse(
        chat.authless_chat_controller(history, req.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # NOTE do we need X-Thread-Id & X-Message-Id
        },
    )


# ---------------------------------------------------------------------------------


@router.post("/new_thread", status_code=201)
async def create_chat_thread(
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await chat.create_chat_thread_controller(access_token, db)
    # Let frontend redirect to /chat/{id}


# ---------------------------------------------------------------------------------


@router.post("/base/{thread_id}", status_code=200)
async def chat_(
    req: ChatRequest,
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
    async_db_session: Annotated[async_sessionmaker[AsyncSession], Depends(get_async_db_session)],
):
    lc_history, ai_msg, llm_model = await chat.authenticated_chat_controller_2(req.prompt, thread_id, access_token, db)
    db.expunge(ai_msg)  # detach — ai_msg must not stay bound to the sync session

    return StreamingResponse(
        chat.generator(req.prompt, lc_history, ai_msg, async_db_session, thread_id, llm_model=llm_model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------------


@router.get("/base/get_messages/{thread_id}", status_code=200)
async def get_messages(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await chat.get_messages_controller(thread_id, access_token, db)


# Model selection endpoints
# ---------------------------------------------------------------------------------


@router.get("/base/{thread_id}/models", status_code=200)
async def get_thread_models(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await chat.get_thread_models_controller(thread_id, access_token, db)


# ---------------------------------------------------------------------------------


@router.patch("/base/{thread_id}/model", status_code=200)
async def update_thread_model(
    thread_id: str,
    req: UpdateModelRequest,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await chat.update_thread_model_controller(thread_id, req.model, access_token, db)


# ---------------------------------------------------------------------------------


@router.get("/base/get_all_thread_titles", response_model=list[dict[str, str]], status_code=200)
async def get_all_thread_titles(
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, str]]:
    return await chat.get_all_thread_titles_controller(access_token, db)


# ---------------------------------------------------------------------------------


@router.patch("/base/{thread_id}/title", status_code=200)
async def update_thread_title(
    thread_id: str,
    req: UpdateTitleRequest,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await chat.update_thread_title_controller(thread_id, req.title, access_token, db)


# ---------------------------------------------------------------------------------


@router.delete("/base/{thread_id}", status_code=200)
async def delete_chat_thread(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return await chat.delete_chat_thread_controller(thread_id, access_token, db)
