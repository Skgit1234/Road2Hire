from fastapi import APIRouter, Depends, HTTPException

from Api.profile import get_current_user
from Models.user import User
from Schemas.assistant import AssistantMessageRequest


router = APIRouter(prefix="/assistant", tags=["Career Assistant"])


@router.post(
    "/messages",
    status_code=503,
    responses={
        503: {
            "description": (
                "Assistant is unavailable because the project has no RAG "
                "retrieval pipeline or configured local language model."
            )
        }
    },
)
def send_assistant_message(
    request: AssistantMessageRequest,
    user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=503,
        detail={
            "message": "Career assistant is not configured.",
            "reason": (
                "The repository contains a skill knowledge graph and embedding "
                "helper, but no retrieval corpus, RAG/chat pipeline, or "
                "configured local language model."
            ),
            "accepted_message_length": len(request.message),
        },
    )
