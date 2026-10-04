from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.middleware import decode_access_token
from app.langchain.evaluator import RAGEvaluator
from app.types import TokenPayload

router = APIRouter(prefix="/v2/evaluation", tags=["evaluation"])

# Optional auth scheme
oauth_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user_optional(token: Annotated[str | None, Depends(oauth_scheme_optional)] = None) -> TokenPayload | None:
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


class EvaluationRequest(BaseModel):
    answer: str = Field(..., min_length=1, description="The generated answer to evaluate.")
    sources: Any = Field(default=None, description="The retrieved sources/chunks or source references.")
    query: str | None = Field(default=None, description="Optional user prompt / question.")
    llm_model: str | None = Field(default=None, description="Optional LLM model slug to use as judge.")


class EvaluationResponse(BaseModel):
    quality: float = Field(..., description="Quality score between 0.0 and 1.0.")
    quality_reason: str = Field(..., description="Short explanation for the quality score.")
    faithfulness: float = Field(..., description="Faithfulness score between 0.0 and 1.0.")
    faithfulness_reason: str = Field(..., description="Short explanation for the faithfulness score.")
    # Map "Short reason" as alias/field as requested in PlanOfAction.md
    short_reason: str = Field(..., alias="Short reason", description="Concise reason summarizing the score.")

    model_config = {
        "populate_by_name": True,
    }


@router.post("", response_model=EvaluationResponse, status_code=200)
@router.post("/evaluate", response_model=EvaluationResponse, status_code=200)
async def evaluate_rag_response(
    req: EvaluationRequest,
    user: Annotated[TokenPayload | None, Depends(get_current_user_optional)] = None,
):
    """Calculate quality and faithfulness scores for a given answer and sources."""
    if not req.answer or not req.answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    try:
        result = await RAGEvaluator.aevaluate(
            answer=req.answer,
            sources=req.sources,
            query=req.query,
            llm_model=req.llm_model,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Evaluation endpoint error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate answer quality and faithfulness: {str(e)}",
        )
