from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Conversation, Message
from backend.schemas import ConversationCreate, ConversationResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> Conversation:
    title = (payload.title or "New chat").strip() or "New chat"
    conversation = Conversation(title=title[:200])
    db.add(conversation)
    try:
        db.commit()
        db.refresh(conversation)
    except Exception as exc:
        db.rollback()
        logger.error("Could not create conversation (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not create conversation") from exc
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(conversation_id: UUID, db: Session = Depends(get_db)) -> list[Message]:
    if db.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list(db.scalars(statement))


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)) -> Response:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Could not delete conversation %s (%s)", conversation_id, type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not delete conversation") from exc
    return Response(status_code=204)
