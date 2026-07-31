"""Conversation persistence models.

Only USER and final ASSISTANT-answer messages are stored per turn - not
the intermediate tool-call/tool-result churn a single turn's agent loop
produces internally (see app/routers/chat.py). Tool calls are an
implementation detail of HOW one turn produces its answer, not part of
the conversation's actual semantic content; a later turn doesn't need
to see "the agent called get_telemetry", just what was asked and
answered. Keeps storage lean and keeps token-budget truncation (see
app/services/history.py) simple - it only ever trims real conversational
turns, never has to reason about tool-call structure.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
