"""
StudyMind AI - Export Router
"""

import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User, GeneratedContent
from schemas import ExportRequest
from services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.post("/pdf")
def export_pdf(
    data: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export content as PDF."""
    content = _get_export_content(data, db, current_user)
    export = ExportService()
    pdf_bytes = export.export_pdf(content, data.title or "StudyMind Export")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={data.title or 'export'}.pdf"},
    )


@router.post("/docx")
def export_docx(
    data: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export content as DOCX."""
    content = _get_export_content(data, db, current_user)
    export = ExportService()
    docx_bytes = export.export_docx(content, data.title or "StudyMind Export")
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={data.title or 'export'}.docx"},
    )


@router.post("/txt")
def export_txt(
    data: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export content as TXT."""
    content = _get_export_content(data, db, current_user)
    export = ExportService()
    txt_bytes = export.export_txt(content, data.title or "StudyMind Export")
    return StreamingResponse(
        io.BytesIO(txt_bytes),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={data.title or 'export'}.txt"},
    )


def _get_export_content(data: ExportRequest, db: Session, user: User):
    """Get content for export based on request."""
    if data.content_id:
        item = db.query(GeneratedContent).filter(
            GeneratedContent.id == data.content_id,
            GeneratedContent.user_id == user.id,
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail="Content not found")
        return item.content_json

    if data.collection_id and data.content_type == "questions":
        from services.duplicate_detector import DuplicateDetector
        detector = DuplicateDetector(db)
        return detector.generate_consolidated_document(data.collection_id)

    raise HTTPException(status_code=400, detail="Provide content_id or collection_id with content_type")
