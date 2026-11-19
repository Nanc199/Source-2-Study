"""
StudyMind AI - Sources Router
"""

import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User, Collection, Source
from schemas import SourceResponse, SourceUploadResponse, URLSourceRequest, YouTubeSourceRequest
from config import settings

router = APIRouter(prefix="/api", tags=["Sources"])


def _process_source_bg(source_id: int):
    """Background task to process a source."""
    from database import SessionLocal
    from services.document_processor import DocumentProcessor
    db = SessionLocal()
    try:
        processor = DocumentProcessor(db)
        processor.process_source(source_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Background processing error: {e}")
    finally:
        db.close()


@router.post("/collections/{collection_id}/sources/upload", response_model=SourceUploadResponse)
async def upload_files(
    collection_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload multiple files to a collection."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.user_id == current_user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    created_sources = []
    rejected_files = []

    for file in files:
        # Validate file extension
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            rejected_files.append(f"{file.filename or 'Unnamed file'}: unsupported format")
            continue

        # Determine file type
        file_type_map = {
            ".pdf": "pdf", ".docx": "docx", ".pptx": "pptx",
            ".jpg": "image", ".jpeg": "image", ".png": "image",
        }
        file_type = file_type_map.get(ext, "pdf")

        # Save file
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        
        content = await file.read()
        file_size = len(content)

        # Validate file size
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            rejected_files.append(
                f"{file.filename}: exceeds the {settings.MAX_FILE_SIZE_MB} MB per-file limit"
            )
            continue

        with open(file_path, "wb") as f:
            f.write(content)

        source = Source(
            collection_id=collection_id,
            user_id=current_user.id,
            filename=unique_name,
            original_filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            status="pending",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        created_sources.append(source)

        # Trigger background processing
        background_tasks.add_task(_process_source_bg, source.id)

    if not created_sources:
        raise HTTPException(
            status_code=400,
            detail="No files were uploaded. " + ("; ".join(rejected_files) or "Select a supported file under the size limit."),
        )

    return SourceUploadResponse(
        message=(
            f"{len(created_sources)} file(s) uploaded and queued for processing"
            + (f". Skipped: {'; '.join(rejected_files)}" if rejected_files else "")
        ),
        sources=[
            SourceResponse(
                id=s.id, collection_id=s.collection_id, filename=s.filename,
                original_filename=s.original_filename, file_type=s.file_type,
                file_size=s.file_size, url=s.url, status=s.status,
                error_message=s.error_message, page_count=s.page_count,
                created_at=s.created_at,
            )
            for s in created_sources
        ],
    )


@router.post("/collections/{collection_id}/sources/url", response_model=SourceResponse)
def add_url_source(
    collection_id: int,
    data: URLSourceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a website URL as a source."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.user_id == current_user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    source = Source(
        collection_id=collection_id,
        user_id=current_user.id,
        original_filename=data.title or data.url,
        file_type="url",
        url=data.url,
        status="pending",
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    background_tasks.add_task(_process_source_bg, source.id)

    return SourceResponse(
        id=source.id, collection_id=source.collection_id, filename=source.filename,
        original_filename=source.original_filename, file_type=source.file_type,
        file_size=source.file_size, url=source.url, status=source.status,
        error_message=source.error_message, page_count=source.page_count,
        created_at=source.created_at,
    )


@router.post("/collections/{collection_id}/sources/youtube", response_model=SourceResponse)
def add_youtube_source(
    collection_id: int,
    data: YouTubeSourceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a YouTube video as a source."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.user_id == current_user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    source = Source(
        collection_id=collection_id,
        user_id=current_user.id,
        original_filename=data.title or f"YouTube: {data.url}",
        file_type="youtube",
        url=data.url,
        status="pending",
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    background_tasks.add_task(_process_source_bg, source.id)

    return SourceResponse(
        id=source.id, collection_id=source.collection_id, filename=source.filename,
        original_filename=source.original_filename, file_type=source.file_type,
        file_size=source.file_size, url=source.url, status=source.status,
        error_message=source.error_message, page_count=source.page_count,
        created_at=source.created_at,
    )


@router.get("/collections/{collection_id}/sources", response_model=List[SourceResponse])
def list_sources(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sources in a collection."""
    sources = (
        db.query(Source)
        .filter(Source.collection_id == collection_id, Source.user_id == current_user.id)
        .order_by(Source.created_at.desc())
        .all()
    )
    return [
        SourceResponse(
            id=s.id, collection_id=s.collection_id, filename=s.filename,
            original_filename=s.original_filename, file_type=s.file_type,
            file_size=s.file_size, url=s.url, status=s.status,
            error_message=s.error_message, page_count=s.page_count,
            created_at=s.created_at,
        )
        for s in sources
    ]


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a source."""
    source = (
        db.query(Source)
        .filter(Source.id == source_id, Source.user_id == current_user.id)
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Delete file if exists
    if source.file_path and os.path.exists(source.file_path):
        try:
            os.remove(source.file_path)
        except OSError:
            pass

    db.delete(source)
    db.commit()


@router.post("/sources/{source_id}/reprocess", response_model=SourceResponse)
def reprocess_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reprocess a source."""
    source = (
        db.query(Source)
        .filter(Source.id == source_id, Source.user_id == current_user.id)
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.status = "pending"
    source.error_message = None
    db.commit()
    db.refresh(source)

    background_tasks.add_task(_process_source_bg, source.id)

    return SourceResponse(
        id=source.id, collection_id=source.collection_id, filename=source.filename,
        original_filename=source.original_filename, file_type=source.file_type,
        file_size=source.file_size, url=source.url, status=source.status,
        error_message=source.error_message, page_count=source.page_count,
        created_at=source.created_at,
    )
