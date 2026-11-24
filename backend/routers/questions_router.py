"""
Source2Study - Questions & Duplicate Detection Router
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import io

from database import get_db
from auth import get_current_user
from models import User, Collection, ExtractedQuestion, DuplicateGroup, Source
from schemas import (
    ExtractedQuestionResponse, DuplicateGroupResponse, DuplicateDetectionRequest,
    DuplicateDetectionResult, GroupUpdateRequest, MergeGroupsRequest, RemoveQuestionRequest,
)

router = APIRouter(prefix="/api", tags=["Questions"])


class DeduplicateDocumentsRequest(BaseModel):
    source_ids: List[int] = Field(..., min_length=1)


def _deduplicate_selected_documents(collection_id: int, source_ids: List[int], db: Session, user: User):
    collection = db.query(Collection).filter(
        Collection.id == collection_id, Collection.user_id == user.id
    ).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    requested_ids = list(dict.fromkeys(source_ids))
    selected = db.query(Source).filter(
        Source.collection_id == collection_id,
        Source.user_id == user.id,
        Source.id.in_(requested_ids),
    ).all()
    if len(selected) != len(requested_ids):
        raise HTTPException(status_code=404, detail="One or more selected files were not found in this collection")

    pending = [s.original_filename or s.filename for s in selected if s.status in ("pending", "processing")]
    if pending:
        raise HTTPException(status_code=409, detail="Wait for all selected files to finish processing before removing duplicates")
    failed = [f"{s.original_filename or s.filename}: {s.error_message or 'processing failed'}" for s in selected if s.status != "completed"]
    if failed:
        raise HTTPException(status_code=400, detail="Some selected files could not be read: " + "; ".join(failed))

    from models import ExtractedChunk
    chunks = db.query(ExtractedChunk).filter(
        ExtractedChunk.collection_id == collection_id,
        ExtractedChunk.source_id.in_(requested_ids),
    ).order_by(ExtractedChunk.source_id, ExtractedChunk.chunk_index).all()
    if not chunks:
        raise HTTPException(status_code=400, detail="No extracted text found in the selected files")

    chunks_by_source = {}
    for chunk in chunks:
        chunks_by_source.setdefault(chunk.source_id, []).append(chunk)
    from services.document_deduplicator import DocumentDeduplicator
    result = DocumentDeduplicator().deduplicate(selected, chunks_by_source)
    if not result["content"]:
        raise HTTPException(status_code=400, detail="No readable text found in the selected files")
    return result


@router.post("/collections/{collection_id}/deduplicate-documents")
def deduplicate_documents(
    collection_id: int,
    data: DeduplicateDocumentsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a preview of unique passages from selected completed documents."""
    result = _deduplicate_selected_documents(collection_id, data.source_ids, db, current_user)
    preview_limit = 12000
    return {
        **result,
        "content": result["content"][:preview_limit],
        "preview_truncated": len(result["content"]) > preview_limit,
    }


@router.post("/collections/{collection_id}/deduplicate-documents/export")
def export_deduplicated_documents(
    collection_id: int,
    data: DeduplicateDocumentsRequest,
    format: str = "pdf",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the duplicate-free document as PDF, DOCX, or TXT."""
    export_format = format.lower()
    if export_format not in {"pdf", "docx", "txt"}:
        raise HTTPException(status_code=400, detail="Format must be pdf, docx, or txt")
    result = _deduplicate_selected_documents(collection_id, data.source_ids, db, current_user)
    from services.export_service import ExportService
    export = ExportService()
    content = {"content": result["content"]}
    if export_format == "pdf":
        file_bytes = export.export_pdf(content, result["title"])
        media_type = "application/pdf"
    elif export_format == "docx":
        file_bytes = export.export_docx(content, result["title"])
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        file_bytes = export.export_txt(content, result["title"])
        media_type = "text/plain"
    filename = f"duplicate_free_study_material.{export_format}"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/collections/{collection_id}/detect-duplicates", response_model=DuplicateDetectionResult)
def detect_duplicates(
    collection_id: int,
    data: DuplicateDetectionRequest = DuplicateDetectionRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run duplicate detection on all questions in a collection or selected sources."""
    collection = db.query(Collection).filter(
        Collection.id == collection_id, Collection.user_id == current_user.id
    ).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    from services.duplicate_detector import DuplicateDetector
    detector = DuplicateDetector(db)
    result = detector.detect_duplicates(
        collection_id,
        current_user.id,
        similarity_threshold=data.similarity_threshold,
        use_llm_verification=data.use_llm_verification,
        source_ids=data.source_ids,
    )
    # Ensure legacy compatibility fields are filled
    result["groups_created"] = result.get("unique_questions", 0)
    result["duplicate_questions"] = result.get("total_duplicate_occurrences", 0)
    result["most_frequent_questions"] = [
        {"question": g["canonical_question"], "frequency": g["frequency"], "topic": g.get("topic")}
        for g in result.get("repeated_question_groups", [])[:10]
    ]
    return DuplicateDetectionResult(**result)


@router.post("/collections/{collection_id}/export-unique-questions-pdf")
def export_unique_questions_pdf(
    collection_id: int,
    data: DuplicateDetectionRequest = DuplicateDetectionRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download a PDF containing exclusively unique questions."""
    collection = db.query(Collection).filter(
        Collection.id == collection_id, Collection.user_id == current_user.id
    ).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    from services.duplicate_detector import DuplicateDetector
    from services.export_service import ExportService

    detector = DuplicateDetector(db)
    result = detector.detect_duplicates(
        collection_id,
        current_user.id,
        similarity_threshold=data.similarity_threshold,
        use_llm_verification=data.use_llm_verification,
        source_ids=data.source_ids,
    )

    export = ExportService()
    pdf_bytes = export.export_unique_questions_pdf(
        questions=result.get("unique_questions_list", []),
        title=f"Source2Study - Unique Questions Bank ({collection.name})",
        stats=result,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="unique_questions_bank.pdf"'},
    )


@router.post("/collections/{collection_id}/export-repeated-questions-pdf")
def export_repeated_questions_pdf(
    collection_id: int,
    data: DuplicateDetectionRequest = DuplicateDetectionRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download a PDF report containing exclusively repeated questions and occurrences."""
    collection = db.query(Collection).filter(
        Collection.id == collection_id, Collection.user_id == current_user.id
    ).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    from services.duplicate_detector import DuplicateDetector
    from services.export_service import ExportService

    detector = DuplicateDetector(db)
    result = detector.detect_duplicates(
        collection_id,
        current_user.id,
        similarity_threshold=data.similarity_threshold,
        use_llm_verification=data.use_llm_verification,
        source_ids=data.source_ids,
    )

    export = ExportService()
    pdf_bytes = export.export_repeated_questions_pdf(
        repeated_groups=result.get("repeated_question_groups", []),
        title=f"Source2Study - Repeated Questions Analysis ({collection.name})",
        stats=result,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="repeated_questions_analysis.pdf"'},
    )


@router.get("/collections/{collection_id}/questions", response_model=List[ExtractedQuestionResponse])
def get_questions(
    collection_id: int,
    source_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all extracted questions for a collection."""
    query = db.query(ExtractedQuestion).filter(
        ExtractedQuestion.collection_id == collection_id,
        ExtractedQuestion.user_id == current_user.id,
    )
    if source_id:
        query = query.filter(ExtractedQuestion.source_id == source_id)
    if search:
        query = query.filter(ExtractedQuestion.question_text.ilike(f"%{search}%"))

    questions = query.order_by(ExtractedQuestion.created_at).all()
    result = []
    for q in questions:
        source = db.query(Source).filter(Source.id == q.source_id).first()
        result.append(ExtractedQuestionResponse(
            id=q.id, source_id=q.source_id, collection_id=q.collection_id,
            question_text=q.question_text, normalized_text=q.normalized_text,
            question_type=q.question_type, page_number=q.page_number,
            year=q.year, source_filename=source.original_filename if source else None,
            created_at=q.created_at,
        ))
    return result


@router.get("/collections/{collection_id}/duplicate-groups")
def get_duplicate_groups(
    collection_id: int,
    sort_by: str = "frequency",
    filter_year: Optional[str] = None,
    filter_frequency: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get duplicate question groups."""
    from services.duplicate_detector import DuplicateDetector
    detector = DuplicateDetector(db)
    return detector.get_groups(
        collection_id,
        sort_by=sort_by,
        filter_year=filter_year,
        filter_frequency=filter_frequency,
        search=search,
    )


@router.get("/collections/{collection_id}/question-stats")
def get_question_stats(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get question statistics for a collection."""
    from services.duplicate_detector import DuplicateDetector
    detector = DuplicateDetector(db)
    return detector.get_stats(collection_id)


@router.put("/duplicate-groups/{group_id}")
def update_group(
    group_id: int,
    data: GroupUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a duplicate group."""
    group = db.query(DuplicateGroup).filter(
        DuplicateGroup.id == group_id, DuplicateGroup.user_id == current_user.id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if data.canonical_question is not None:
        group.canonical_question = data.canonical_question
    if data.topic is not None:
        group.topic = data.topic
    db.commit()
    return {"message": "Group updated"}


@router.post("/duplicate-groups/merge")
def merge_groups(
    data: MergeGroupsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Merge multiple duplicate groups."""
    from services.duplicate_detector import DuplicateDetector
    detector = DuplicateDetector(db)
    return detector.merge_groups(data.group_ids, current_user.id)


@router.post("/duplicate-groups/{group_id}/remove-question")
def remove_question_from_group(
    group_id: int,
    data: RemoveQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a question from a duplicate group."""
    from services.duplicate_detector import DuplicateDetector
    detector = DuplicateDetector(db)
    return detector.remove_question_from_group(group_id, data.question_id, current_user.id)


@router.post("/collections/{collection_id}/export-questions")
def export_questions(
    collection_id: int,
    format: str = "pdf",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export consolidated question document."""
    from services.duplicate_detector import DuplicateDetector
    from services.export_service import ExportService

    detector = DuplicateDetector(db)
    document = detector.generate_consolidated_document(collection_id)
    export = ExportService()

    if format == "pdf":
        data = export.export_pdf(document, "Consolidated Question Bank")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=consolidated_questions.pdf"},
        )
    elif format == "docx":
        data = export.export_docx(document, "Consolidated Question Bank")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=consolidated_questions.docx"},
        )
    else:
        data = export.export_txt(document, "Consolidated Question Bank")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=consolidated_questions.txt"},
        )
