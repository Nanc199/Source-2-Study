"""
Source2Study - Chat Router
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User, Collection, ChatSession, ChatMessage
from schemas import ChatSessionCreate, ChatSessionResponse, ChatMessageCreate, ChatMessageResponse

router = APIRouter(prefix="/api", tags=["Chat"])


@router.get("/collections/{collection_id}/chat/sessions", response_model=List[ChatSessionResponse])
def list_sessions(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List chat sessions for a collection."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.collection_id == collection_id, ChatSession.user_id == current_user.id)
        .filter(ChatSession.messages.any())
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    result = []
    repaired_legacy_titles = False
    for s in sessions:
        if s.title in (None, "", "New Chat"):
            first_message = next((m for m in s.messages if m.role == "user"), None)
            if first_message:
                s.title = first_message.content[:100]
                repaired_legacy_titles = True
        msg_count = len(s.messages)
        result.append(ChatSessionResponse(
            id=s.id, collection_id=s.collection_id, title=s.title,
            created_at=s.created_at, updated_at=s.updated_at, message_count=msg_count,
        ))
    if repaired_legacy_titles:
        db.commit()
    return result


@router.post("/collections/{collection_id}/chat/sessions", response_model=ChatSessionResponse)
def create_session(
    collection_id: int,
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session."""
    collection = db.query(Collection).filter(
        Collection.id == collection_id, Collection.user_id == current_user.id
    ).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    session = ChatSession(
        user_id=current_user.id,
        collection_id=collection_id,
        title=data.title or "New Chat",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionResponse(
        id=session.id, collection_id=session.collection_id, title=session.title,
        created_at=session.created_at, updated_at=session.updated_at, message_count=0,
    )


@router.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get messages for a chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        ChatMessageResponse(
            id=m.id, session_id=m.session_id, role=m.role, content=m.content,
            sources_json=m.sources_json, created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def send_message(
    session_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get AI response."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)
    db.commit()

    # Get chat history
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    chat_history = [{"role": m.role, "content": m.content} for m in history]

    # Generate AI response
    from services.rag_service import RAGService
    rag = RAGService()
    result = rag.generate_response(
        str(session.collection_id),
        data.content,
        chat_history=chat_history,
    )

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=result["content"],
        sources_json=result.get("sources"),
    )
    db.add(assistant_msg)

    # Update session title if first message
    if len(history) <= 1:
        session.title = data.content[:100]

    db.commit()
    db.refresh(assistant_msg)

    return ChatMessageResponse(
        id=assistant_msg.id, session_id=assistant_msg.session_id,
        role=assistant_msg.role, content=assistant_msg.content,
        sources_json=assistant_msg.sources_json, created_at=assistant_msg.created_at,
    )


@router.delete("/chat/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
