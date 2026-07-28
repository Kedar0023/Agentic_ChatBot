import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.app_configs import getAppConfig
from app.core.logging import logger
from app.core.middleware import authenticate_user
from app.database.db import get_db
from app.langchain.llm import AVAILABLE_MODELS, DEFAULT_MODEL, list_models
from app.store.MessageStore import MessageStore
from app.store.ThreadStore import ThreadStore
from app.store.UserStore import UserStore
from app.types import TokenPayload, UpdateModelRequest, UpdateTitleRequest

router = APIRouter(prefix="/v2/thread", tags=["thread"])
AppConfig = getAppConfig()


# --------------------------------------------------------------------------------
@router.post("/create", status_code=201)
async def create_chat_thread(
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    thread_id = uuid.uuid4()

    user_id = int(access_token.sub)

    new_thread = ThreadStore.create(db, thread_id, user_id)
    try:
        db.commit()
        db.refresh(new_thread)
    except Exception as e:
        db.rollback()
        logger.error("Thread creation failed user_id=%s", user_id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during thread creation.",
                "error": str(e.__cause__),
            },
        )

    logger.info("Thread created thread_id=%s user_id=%s", thread_id, user_id)
    return {"thread_id": str(thread_id)}


# --------------------------------------------------------------------------------


@router.get("/{thread_id}/messages", status_code=200)
async def get_messages(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    thread = ThreadStore.get_for_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    messages = MessageStore.get_ordered_msgs_by_thread_id(db, thread_id)

    return {"messages": messages}


# --------------------------------------------------------------------------------


@router.get("/{thread_id}/models", status_code=200)
async def get_thread_models(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    thread = ThreadStore.get_for_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {
        "current_model": thread.llm_model or DEFAULT_MODEL,
        "default_model": DEFAULT_MODEL,
        "models": list_models(),
    }


# --------------------------------------------------------------------------------


@router.patch("/{thread_id}/model", status_code=200)
async def update_thread_model(
    thread_id: str,
    req: UpdateModelRequest,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if req.model not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{req.model}'. Use GET /models to see available options.",
        )

    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    thread = ThreadStore.get_for_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    ThreadStore.update_model(thread, req.model)
    try:
        db.commit()
        db.refresh(thread)
    except Exception as e:
        db.rollback()
        logger.error("Model update failed thread_id=%s", thread_id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to update model.",
                "error": str(e.__cause__ or e),
            },
        )

    logger.info("Model updated thread_id=%s model=%s", thread_id, req.model)
    return {
        "thread_id": str(thread.id),
        "model": thread.llm_model,
    }


# --------------------------------------------------------------------------------


@router.delete("/{thread_id}", status_code=200)
async def delete_chat_thread(
    thread_id: str,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    thread = ThreadStore.get_for_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        ThreadStore.delete(db, thread)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Thread deletion failed thread_id=%s", thread_id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to delete chat thread.",
                "error": str(e.__cause__ or e),
            },
        )

    logger.info("Thread deleted thread_id=%s user_id=%s", thread_id, user_id)
    return {"message": "Thread deleted successfully", "thread_id": thread_id}


# --------------------------------------------------------------------------------


@router.patch("/{thread_id}/title", status_code=200)
async def update_thread_title(
    thread_id: str,
    req: UpdateTitleRequest,
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    thread = ThreadStore.get_for_user(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=403, detail="Forbidden")

    ThreadStore.update_title(thread, req.title)
    try:
        db.commit()
        db.refresh(thread)
    except Exception as e:
        db.rollback()
        logger.error("Title update failed thread_id=%s", thread_id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to update thread title.",
                "error": str(e.__cause__ or e),
            },
        )

    logger.info("Thread title updated thread_id=%s title=%s", thread_id, req.title)
    return {
        "thread_id": str(thread.id),
        "title": thread.title,
    }


# --------------------------------------------------------------------------------
@router.get("/list_threads", response_model=list[dict[str, str]], status_code=200)
async def get_all_thread_titles(
    access_token: Annotated[TokenPayload, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, str]]:
    try:
        user_id = int(access_token.sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token payload.")

    user = UserStore.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        threads: list[dict[str, str]] = UserStore.get_all_thread_titles(db, user_id)
        return threads
    except Exception as e:
        logger.error("Failed to fetch thread titles user_id=%s", user_id, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred while fetching thread titles.",
                "error": str(e.__cause__ or e),
            },
        )
