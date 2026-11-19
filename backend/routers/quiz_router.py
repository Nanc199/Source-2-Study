"""
StudyMind AI - Quiz Router
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User, QuizAttempt
from schemas import QuizGenerateRequest, QuizAttemptCreate, QuizAttemptResponse

router = APIRouter(prefix="/api", tags=["Quiz"])


@router.post("/collections/{collection_id}/quiz/generate")
def generate_quiz(
    collection_id: int,
    data: QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a quiz from collection content."""
    from services.quiz_service import QuizService
    service = QuizService(db)
    result = service.generate_quiz(
        collection_id,
        data.question_count,
        data.difficulty,
        data.question_type,
        data.source_ids,
    )
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=result.get("status_code", 400), detail=result["error"])
    return result


@router.post("/quiz/submit", response_model=QuizAttemptResponse)
def submit_quiz(
    data: QuizAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a quiz attempt for scoring."""
    from services.quiz_service import QuizService
    service = QuizService(db)
    scored = service.score_quiz(data.questions_json, data.answers_json)

    attempt = QuizAttempt(
        user_id=current_user.id,
        collection_id=data.collection_id,
        title=data.title or "Quiz",
        difficulty=data.difficulty,
        question_count=len(data.questions_json),
        score=scored["score"],
        total_marks=scored["total_marks"],
        time_taken_seconds=data.time_taken_seconds,
        questions_json=data.questions_json,
        answers_json=scored["results"],
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return QuizAttemptResponse(
        id=attempt.id, collection_id=attempt.collection_id, title=attempt.title,
        difficulty=attempt.difficulty, question_count=attempt.question_count,
        score=attempt.score, total_marks=attempt.total_marks,
        time_taken_seconds=attempt.time_taken_seconds,
        questions_json=attempt.questions_json, answers_json=attempt.answers_json,
        created_at=attempt.created_at,
    )


@router.get("/quiz/history", response_model=List[QuizAttemptResponse])
def quiz_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get quiz history."""
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )
    return [
        QuizAttemptResponse(
            id=a.id, collection_id=a.collection_id, title=a.title,
            difficulty=a.difficulty, question_count=a.question_count,
            score=a.score, total_marks=a.total_marks,
            time_taken_seconds=a.time_taken_seconds,
            questions_json=a.questions_json, answers_json=a.answers_json,
            created_at=a.created_at,
        )
        for a in attempts
    ]


@router.get("/quiz/{quiz_id}", response_model=QuizAttemptResponse)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific quiz attempt."""
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.id == quiz_id, QuizAttempt.user_id == current_user.id
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return QuizAttemptResponse(
        id=attempt.id, collection_id=attempt.collection_id, title=attempt.title,
        difficulty=attempt.difficulty, question_count=attempt.question_count,
        score=attempt.score, total_marks=attempt.total_marks,
        time_taken_seconds=attempt.time_taken_seconds,
        questions_json=attempt.questions_json, answers_json=attempt.answers_json,
        created_at=attempt.created_at,
    )
