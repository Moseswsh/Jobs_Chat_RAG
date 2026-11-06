from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Conversation, Message
from backend.rag import RAGPipeline
from backend.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


def respond_to_chat(payload: ChatRequest, db: Session, rag: RAGPipeline) -> ChatResponse:
    conversation = db.get(Conversation, payload.conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    history_limit = max(2, min(20, int(os.getenv("CONVERSATION_HISTORY_MESSAGES", "8"))))
    recent_statement = (
        select(Message)
        .where(Message.conversation_id == payload.conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(history_limit)
    )
    history_rows = list(db.scalars(recent_statement))
    history_rows.reverse()
    history = [{"role": row.role, "content": row.content} for row in history_rows]

    user_message = Message(conversation_id=payload.conversation_id, role="user", content=payload.message)
    db.add(user_message)
    conversation.updated_at = datetime.now(timezone.utc)
    if conversation.title == "New chat":
        conversation.title = payload.message.strip().replace("\n", " ")[:80] or "New chat"
    try:
        db.commit()
        db.refresh(conversation)
    except Exception as exc:
        db.rollback()
        logger.error(
            "Could not persist user message for conversation %s (%s)",
            payload.conversation_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="The message could not be saved. Please retry.") from exc

    retrieval_terms = [item["content"] for item in history if item["role"] == "user"][-3:]
    retrieval_query = "\n".join([*retrieval_terms, payload.message])
    try:
        documents = rag.search(retrieval_query)
        answer = rag.generate_answer(payload.message, documents, history=history)
    except Exception as exc:
        logger.error(
            "Chat generation failed for conversation %s (%s)",
            payload.conversation_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="The assistant could not generate a reply. Please try again.") from exc

    try:
        db.add(Message(conversation_id=payload.conversation_id, role="assistant", content=answer))
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            "Could not persist assistant reply for conversation %s (%s)",
            payload.conversation_id,
            type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail="The reply could not be saved. Please retry.") from exc

    return ChatResponse(
        conversation_id=payload.conversation_id,
        title=conversation.title,
        reply=answer,
        sources=list(dict.fromkeys(document.source for document in documents)),
    )
