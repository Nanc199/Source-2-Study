"""
Source2Study - Dashboard Router
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from auth import get_current_user
from models import (
    User, Collection, Source, ExtractedChunk, ExtractedQuestion,
    QuizAttempt, GeneratedContent, DuplicateGroup, Flashcard,
)
from schemas import DashboardStats, RecentActivity

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics."""
    uid = current_user.id
    total_collections = db.query(Collection).filter(Collection.user_id == uid).count()
    total_sources = db.query(Source).filter(Source.user_id == uid).count()
    total_chunks = db.query(ExtractedChunk).join(Source).filter(Source.user_id == uid).count()
    total_questions = db.query(ExtractedQuestion).filter(ExtractedQuestion.user_id == uid).count()
    total_quizzes = db.query(QuizAttempt).filter(QuizAttempt.user_id == uid).count()
    total_generated = db.query(GeneratedContent).filter(GeneratedContent.user_id == uid).count()
    total_flashcards = db.query(Flashcard).filter(Flashcard.user_id == uid).count()
    dup_groups = db.query(DuplicateGroup).filter(DuplicateGroup.user_id == uid).count()

    avg_score = db.query(func.avg(QuizAttempt.score)).filter(
        QuizAttempt.user_id == uid, QuizAttempt.score.isnot(None)
    ).scalar()

    return DashboardStats(
        total_collections=total_collections,
        total_sources=total_sources,
        total_chunks=total_chunks,
        total_questions=total_questions,
        total_quizzes=total_quizzes,
        total_generated=total_generated,
        total_flashcards=total_flashcards,
        duplicate_groups=dup_groups,
        average_quiz_score=round(float(avg_score), 1) if avg_score else None,
    )


@router.get("/recent-activity", response_model=List[RecentActivity])
def recent_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent user activity."""
    uid = current_user.id
    activities = []

    # Recent sources
    recent_sources = (
        db.query(Source)
        .filter(Source.user_id == uid)
        .order_by(Source.created_at.desc())
        .limit(5)
        .all()
    )
    for s in recent_sources:
        coll = db.query(Collection).filter(Collection.id == s.collection_id).first()
        activities.append(RecentActivity(
            type="source_added",
            title=f"Uploaded {s.original_filename or s.filename}",
            description=f"Status: {s.status}",
            timestamp=s.created_at,
            collection_id=s.collection_id,
            collection_name=coll.name if coll else None,
        ))

    # Recent quizzes
    recent_quizzes = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == uid)
        .order_by(QuizAttempt.created_at.desc())
        .limit(5)
        .all()
    )
    for q in recent_quizzes:
        coll = db.query(Collection).filter(Collection.id == q.collection_id).first()
        activities.append(RecentActivity(
            type="quiz_taken",
            title=f"Completed quiz: {q.title}",
            description=f"Score: {q.score}/{q.total_marks}" if q.score is not None else None,
            timestamp=q.created_at,
            collection_id=q.collection_id,
            collection_name=coll.name if coll else None,
        ))

    # Recent generated content
    recent_gen = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.user_id == uid)
        .order_by(GeneratedContent.created_at.desc())
        .limit(5)
        .all()
    )
    for g in recent_gen:
        coll = db.query(Collection).filter(Collection.id == g.collection_id).first()
        activities.append(RecentActivity(
            type="content_generated",
            title=f"Generated {g.title}",
            description=g.content_type,
            timestamp=g.created_at,
            collection_id=g.collection_id,
            collection_name=coll.name if coll else None,
        ))

    # Sort by timestamp descending
    activities.sort(key=lambda a: a.timestamp, reverse=True)
    return activities[:15]
