"""
Source2Study - Quiz Service
Generates and scores interactive quizzes.
"""

import json
import logging
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session
from config import settings

logger = logging.getLogger(__name__)


class QuizService:
    """Generates quizzes and scores attempts."""

    def __init__(self, db: Session):
        self.db = db

    def generate_quiz(
        self,
        collection_id: int,
        question_count: int = 10,
        difficulty: str = "medium",
        question_type: str = "mcq",
        source_ids: Optional[List[int]] = None,
    ) -> List[Dict]:
        """Generate a quiz from collection content."""
        from models import ExtractedChunk
        from services.rag_service import RAGService

        if not settings.GEMINI_API_KEY:
            return {"error": "Gemini API key not configured. Add GEMINI_API_KEY to .env file."}

        # Get content
        query = self.db.query(ExtractedChunk).filter(
            ExtractedChunk.collection_id == collection_id
        )
        if source_ids:
            query = query.filter(ExtractedChunk.source_id.in_(source_ids))

        chunks = query.order_by(ExtractedChunk.chunk_index).all()
        if not chunks:
            return {"error": "No content found. Upload and process documents first."}

        # Bound prompt size and leave a predictable output budget for the quiz.
        content = "\n\n".join(c.content for c in chunks[:40])[:18000]

        difficulty_desc = {
            "easy": "simple, basic concepts, direct questions",
            "medium": "moderate difficulty, requires understanding of concepts",
            "hard": "challenging, requires deep understanding, analytical thinking",
        }

        type_instruction = ""
        if question_type == "mcq":
            type_instruction = """Generate Multiple Choice Questions. Each question must have exactly 4 options (A, B, C, D).
Format: [{"id": 1, "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A", "explanation": "...", "question_type": "mcq", "marks": 1}]"""
        elif question_type == "true_false":
            type_instruction = """Generate True/False questions.
Format: [{"id": 1, "question": "...", "options": ["True", "False"], "correct_answer": "True", "explanation": "...", "question_type": "true_false", "marks": 1}]"""
        else:
            type_instruction = """Generate a mix of MCQ and True/False questions.
MCQ format: {"id": 1, "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A", "explanation": "...", "question_type": "mcq", "marks": 1}
True/False format: {"id": 2, "question": "...", "options": ["True", "False"], "correct_answer": "True", "explanation": "...", "question_type": "true_false", "marks": 1}"""

        prompt = f"""Generate exactly {question_count} quiz questions based on the following study material.

Difficulty: {difficulty} - {difficulty_desc.get(difficulty, 'moderate')}

{type_instruction}

STUDY MATERIAL:
{content}

Generate exactly {question_count} questions. Return ONLY the JSON array, no other text:"""

        rag = RAGService()
        try:
            response = rag._call_gemini(
                prompt,
                max_output_tokens=min(8192, 1200 + question_count * 500),
                json_mode=True,
                timeout_ms=40000,
            )
            
            # Parse JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            questions = json.loads(json_str.strip())
            if isinstance(questions, dict):
                questions = questions.get("questions")
            if not isinstance(questions, list) or not questions:
                raise json.JSONDecodeError("Expected a non-empty JSON array", json_str, 0)
            if len(questions) != question_count:
                logger.warning("Quiz model returned %s of %s requested questions", len(questions), question_count)
                return {"error": "AI returned an incomplete quiz. Please try again."}

            # Validate and fix IDs
            for i, q in enumerate(questions):
                if not isinstance(q, dict) or not q.get("question") or not q.get("correct_answer"):
                    return {"error": "AI returned an incomplete quiz question. Please try again."}
                q["id"] = i + 1
                if "marks" not in q:
                    q["marks"] = 1
                if "question_type" not in q:
                    q["question_type"] = question_type

            return questions

        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract questions manually
            logger.error(f"Failed to parse quiz JSON: {response[:500]}")
            return {"error": "Failed to generate quiz. Please try again."}
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            if any(marker in str(e).upper() for marker in (
                "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                "TIMED OUT", "TIMEOUT", "DEADLINE EXCEEDED",
            )):
                return {"error": "AI service is temporarily busy. Please try again shortly.", "status_code": 503}
            return {"error": f"Quiz generation failed: {str(e)}"}

    def score_quiz(self, questions: List[Dict], answers: List[Dict]) -> Dict:
        """Score a quiz attempt."""
        answer_map = {a["question_id"]: a.get("selected_answer", "") for a in answers}
        
        correct = 0
        total_marks = 0
        scored_marks = 0
        results = []

        for q in questions:
            qid = q.get("id", 0)
            marks = q.get("marks", 1)
            total_marks += marks
            user_answer = answer_map.get(qid, "")
            is_correct = user_answer.strip().upper() == q.get("correct_answer", "").strip().upper()

            if is_correct:
                correct += 1
                scored_marks += marks

            results.append({
                "question_id": qid,
                "question": q.get("question", ""),
                "user_answer": user_answer,
                "correct_answer": q.get("correct_answer", ""),
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
                "marks": marks,
            })

        return {
            "score": scored_marks,
            "total_marks": total_marks,
            "correct_count": correct,
            "total_questions": len(questions),
            "percentage": round((scored_marks / total_marks * 100) if total_marks > 0 else 0, 1),
            "results": results,
        }
