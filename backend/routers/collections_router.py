"""
Source2Study - Collections Router
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User, Collection, Source, ExtractedChunk, ExtractedQuestion, GeneratedContent
from schemas import (
    CollectionCreate, CollectionUpdate, CollectionResponse, CollectionDetail, SourceResponse
)

router = APIRouter(prefix="/api/collections", tags=["Collections"])


@router.get("", response_model=List[CollectionResponse])
def list_collections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all collections for the current user."""
    collections = (
        db.query(Collection)
        .filter(Collection.user_id == current_user.id)
        .order_by(Collection.updated_at.desc())
        .all()
    )
    result = []
    for c in collections:
        source_count = db.query(Source).filter(Source.collection_id == c.id).count()
        chunk_count = db.query(ExtractedChunk).filter(ExtractedChunk.collection_id == c.id).count()
        result.append(CollectionResponse(
            id=c.id, name=c.name, description=c.description,
            created_at=c.created_at, updated_at=c.updated_at,
            source_count=source_count, chunk_count=chunk_count,
        ))
    return result


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    data: CollectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new collection."""
    collection = Collection(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return CollectionResponse(
        id=collection.id, name=collection.name, description=collection.description,
        created_at=collection.created_at, updated_at=collection.updated_at,
        source_count=0, chunk_count=0,
    )


@router.get("/{collection_id}", response_model=CollectionDetail)
def get_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get collection details with sources and statistics."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.user_id == current_user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    sources = db.query(Source).filter(Source.collection_id == collection_id).all()
    source_count = len(sources)
    chunk_count = db.query(ExtractedChunk).filter(ExtractedChunk.collection_id == collection_id).count()
    question_count = db.query(ExtractedQuestion).filter(ExtractedQuestion.collection_id == collection_id).count()
    generated_count = db.query(GeneratedContent).filter(GeneratedContent.collection_id == collection_id).count()

    source_responses = [
        SourceResponse(
            id=s.id, collection_id=s.collection_id, filename=s.filename,
            original_filename=s.original_filename, file_type=s.file_type,
            file_size=s.file_size, url=s.url, status=s.status,
            error_message=s.error_message, page_count=s.page_count,
            created_at=s.created_at,
        )
        for s in sources
    ]

    return CollectionDetail(
        id=collection.id, name=collection.name, description=collection.description,
        created_at=collection.created_at, updated_at=collection.updated_at,
        sources=source_responses, source_count=source_count, chunk_count=chunk_count,
        question_count=question_count, generated_count=generated_count,
    )


@router.put("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a collection."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.user_id == current_user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if data.name is not None:
        collection.name = data.name
    if data.description is not None:
        collection.description = data.description

    db.commit()
    db.refresh(collection)
    source_count = db.query(Source).filter(Source.collection_id == collection_id).count()

    return CollectionResponse(
        id=collection.id, name=collection.name, description=collection.description,
        created_at=collection.created_at, updated_at=collection.updated_at,
        source_count=source_count,
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a collection and all its data."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.user_id == current_user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Clean up vector store
    try:
        from services.rag_service import RAGService
        RAGService().delete_collection_data(str(collection_id))
    except Exception:
        pass

    db.delete(collection)
    db.commit()
