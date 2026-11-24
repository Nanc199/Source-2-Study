"""
Source2Study - Study Material Generator Router
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User, Collection, GeneratedContent, Flashcard
from schemas import (
    GenerateContentRequest, GeneratedContentResponse,
    FlashcardCreate, FlashcardResponse,
)

router = APIRouter(prefix="/api", tags=["Study Generator"])


@router.post("/collections/{collection_id}/generate", response_model=GeneratedContentResponse)
def generate_content(
    collection_id: int,
    data: GenerateContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate study material from collection content."""
    collection = db.query(Collection).filter(
        Collection.id == collection_id, Collection.user_id == current_user.id
    ).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    from services.rag_service import RAGService
    rag = RAGService()
    result = rag.generate_content(
        str(collection_id), data.type, data.source_ids, db=db
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=result.get("status_code", 400), detail=result["error"])

    # Save generated content
    title_map = {
        "short_summary": "Short Summary",
        "detailed_summary": "Detailed Summary",
        "short_answers": "Short Answer Questions",
        "long_answers": "Long Answer Questions",
        "mcqs": "Multiple Choice Questions",
        "important_questions": "Important Questions",
        "flashcards": "Flashcards",
        "notes": "Study Notes",
    }

    generated = GeneratedContent(
        user_id=current_user.id,
        collection_id=collection_id,
        content_type=data.type,
        content_json=result,
        source_ids_json=data.source_ids,
        title=title_map.get(data.type, data.type),
    )
    db.add(generated)

    # Also save flashcards to Flashcard table
    if data.type == "flashcards" and isinstance(result, dict):
        content = result.get("content", [])
        if isinstance(content, list):
            for fc in content:
                if isinstance(fc, dict) and "question" in fc and "answer" in fc:
                    flashcard = Flashcard(
                        user_id=current_user.id,
                        collection_id=collection_id,
                        question=fc["question"],
                        answer=fc["answer"],
                    )
                    db.add(flashcard)

    db.commit()
    db.refresh(generated)

    return GeneratedContentResponse(
        id=generated.id, collection_id=generated.collection_id,
        content_type=generated.content_type, content_json=generated.content_json,
        source_ids_json=generated.source_ids_json, title=generated.title,
        created_at=generated.created_at,
    )


@router.get("/collections/{collection_id}/generated", response_model=List[GeneratedContentResponse])
def list_generated(
    collection_id: int,
    content_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List generated content for a collection."""
    query = db.query(GeneratedContent).filter(
        GeneratedContent.collection_id == collection_id,
        GeneratedContent.user_id == current_user.id,
    )
    if content_type:
        query = query.filter(GeneratedContent.content_type == content_type)

    items = query.order_by(GeneratedContent.created_at.desc()).all()
    return [
        GeneratedContentResponse(
            id=g.id, collection_id=g.collection_id, content_type=g.content_type,
            content_json=g.content_json, source_ids_json=g.source_ids_json,
            title=g.title, created_at=g.created_at,
        )
        for g in items
    ]


@router.get("/generated/{content_id}", response_model=GeneratedContentResponse)
def get_generated(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get specific generated content."""
    item = db.query(GeneratedContent).filter(
        GeneratedContent.id == content_id,
        GeneratedContent.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return GeneratedContentResponse(
        id=item.id, collection_id=item.collection_id, content_type=item.content_type,
        content_json=item.content_json, source_ids_json=item.source_ids_json,
        title=item.title, created_at=item.created_at,
    )


@router.delete("/generated/{content_id}", status_code=204)
def delete_generated(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete generated content."""
    item = db.query(GeneratedContent).filter(
        GeneratedContent.id == content_id,
        GeneratedContent.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    db.delete(item)
    db.commit()


# Flashcard routes
@router.get("/collections/{collection_id}/flashcards", response_model=List[FlashcardResponse])
def list_flashcards(
    collection_id: int,
    favorites_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List flashcards for a collection."""
    query = db.query(Flashcard).filter(
        Flashcard.collection_id == collection_id,
        Flashcard.user_id == current_user.id,
    )
    if favorites_only:
        query = query.filter(Flashcard.is_favorite == True)
    cards = query.order_by(Flashcard.created_at.desc()).all()
    return [
        FlashcardResponse(
            id=f.id, collection_id=f.collection_id, question=f.question,
            answer=f.answer, is_favorite=f.is_favorite, created_at=f.created_at,
        )
        for f in cards
    ]


@router.post("/collections/{collection_id}/flashcards", response_model=FlashcardResponse)
def create_flashcard(
    collection_id: int,
    data: FlashcardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a flashcard."""
    card = Flashcard(
        user_id=current_user.id,
        collection_id=collection_id,
        question=data.question,
        answer=data.answer,
        is_favorite=data.is_favorite,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return FlashcardResponse(
        id=card.id, collection_id=card.collection_id, question=card.question,
        answer=card.answer, is_favorite=card.is_favorite, created_at=card.created_at,
    )


@router.put("/flashcards/{flashcard_id}/toggle-favorite", response_model=FlashcardResponse)
def toggle_favorite(
    flashcard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle flashcard favorite status."""
    card = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id, Flashcard.user_id == current_user.id
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    card.is_favorite = not card.is_favorite
    db.commit()
    db.refresh(card)
    return FlashcardResponse(
        id=card.id, collection_id=card.collection_id, question=card.question,
        answer=card.answer, is_favorite=card.is_favorite, created_at=card.created_at,
    )


@router.delete("/flashcards/{flashcard_id}", status_code=204)
def delete_flashcard(
    flashcard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a flashcard."""
    card = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id, Flashcard.user_id == current_user.id
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    db.delete(card)
    db.commit()
