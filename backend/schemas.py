"""
Source2Study - Pydantic Schemas
Request and response schemas for all API endpoints.
"""

import re
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, EmailStr, field_validator


def validate_strong_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter (A-Z)")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter (a-z)")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one numerical digit (0-9)")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]\\/~`]", v):
        raise ValueError("Password must contain at least one special character (@, #, $, %, !, etc.)")
    return v


# ============================================================
# Auth Schemas
# ============================================================

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    password: str = Field(..., max_length=128, description="Password")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_strong_password(v)


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Verification token")


class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Reset token")
    new_password: str = Field(..., max_length=128, description="New strong password")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_strong_password(v)


class MessageResponse(BaseModel):
    message: str
    email: Optional[str] = None


# ============================================================
# Collection Schemas
# ============================================================

class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, max_length=2000, description="Collection description")


class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    source_count: Optional[int] = 0
    chunk_count: Optional[int] = 0

    class Config:
        from_attributes = True


class CollectionDetail(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sources: List["SourceResponse"] = []
    source_count: int = 0
    chunk_count: int = 0
    question_count: int = 0
    generated_count: int = 0

    class Config:
        from_attributes = True


# ============================================================
# Source Schemas
# ============================================================

class SourceResponse(BaseModel):
    id: int
    collection_id: int
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    file_type: str
    file_size: Optional[int] = None
    url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    page_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SourceUploadResponse(BaseModel):
    message: str
    sources: List[SourceResponse]


class URLSourceRequest(BaseModel):
    url: str = Field(..., description="URL to extract content from")
    title: Optional[str] = Field(None, description="Optional title for the source")


class YouTubeSourceRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    title: Optional[str] = Field(None, description="Optional title for the source")


# ============================================================
# Chunk Schemas
# ============================================================

class ChunkResponse(BaseModel):
    id: int
    source_id: int
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============================================================
# Chat Schemas
# ============================================================

class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field("New Chat", max_length=255)


class ChatSessionResponse(BaseModel):
    id: int
    collection_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    sources_json: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Study / Generated Content Schemas
# ============================================================

class GenerateContentRequest(BaseModel):
    type: str = Field(
        ...,
        description="Content type to generate",
        pattern="^(short_summary|detailed_summary|short_answers|long_answers|mcqs|important_questions|flashcards|notes)$"
    )
    source_ids: Optional[List[int]] = Field(None, description="Specific source IDs, or null for all sources")


class GeneratedContentResponse(BaseModel):
    id: int
    collection_id: int
    content_type: str
    content_json: Any
    source_ids_json: Optional[List[int]] = None
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Question / Duplicate Schemas
# ============================================================

class ExtractedQuestionResponse(BaseModel):
    id: int
    source_id: int
    collection_id: int
    question_text: str
    normalized_text: str
    question_type: Optional[str] = None
    page_number: Optional[int] = None
    year: Optional[str] = None
    source_filename: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DuplicateGroupMemberResponse(BaseModel):
    id: int
    question_id: int
    similarity_score: float
    question: Optional[ExtractedQuestionResponse] = None

    class Config:
        from_attributes = True


class DuplicateGroupResponse(BaseModel):
    id: int
    collection_id: int
    canonical_question: str
    topic: Optional[str] = None
    frequency: int
    members: List[DuplicateGroupMemberResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class DuplicateDetectionRequest(BaseModel):
    similarity_threshold: Optional[float] = Field(0.85, ge=0.5, le=1.0)
    use_llm_verification: Optional[bool] = True
    source_ids: Optional[List[int]] = None


class DuplicateDetectionResult(BaseModel):
    total_documents: int
    total_pages_processed: Optional[int] = 0
    total_questions: int
    unique_questions: int
    repeated_groups_count: Optional[int] = 0
    total_duplicate_occurrences: Optional[int] = 0
    duplicate_questions: Optional[int] = 0
    duplicate_percentage: float
    groups_created: Optional[int] = 0
    most_frequent_questions: List[Dict[str, Any]] = []
    repeated_question_groups: List[Dict[str, Any]] = []
    unique_questions_list: List[Dict[str, Any]] = []


class GroupUpdateRequest(BaseModel):
    canonical_question: Optional[str] = None
    topic: Optional[str] = None


class MergeGroupsRequest(BaseModel):
    group_ids: List[int] = Field(..., min_length=2, description="IDs of groups to merge")


class RemoveQuestionRequest(BaseModel):
    question_id: int = Field(..., description="ID of question to remove from group")


# ============================================================
# Quiz Schemas
# ============================================================

class QuizGenerateRequest(BaseModel):
    question_count: int = Field(10, ge=1, le=50, description="Number of questions")
    difficulty: str = Field("medium", description="Difficulty level: easy, medium, hard")
    question_type: str = Field("mcq", description="Question type: mcq, true_false, mixed")
    source_ids: Optional[List[int]] = Field(None, description="Specific source IDs")


class QuizQuestionSchema(BaseModel):
    id: int
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    question_type: str = "mcq"
    marks: float = 1.0


class QuizAttemptCreate(BaseModel):
    collection_id: int
    title: Optional[str] = None
    difficulty: Optional[str] = None
    questions_json: List[Dict[str, Any]]
    answers_json: List[Dict[str, Any]]
    time_taken_seconds: Optional[int] = None


class QuizAttemptResponse(BaseModel):
    id: int
    collection_id: int
    title: Optional[str] = None
    difficulty: Optional[str] = None
    question_count: int
    score: Optional[float] = None
    total_marks: Optional[float] = None
    time_taken_seconds: Optional[int] = None
    questions_json: Any
    answers_json: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Flashcard Schemas
# ============================================================

class FlashcardCreate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    is_favorite: bool = False


class FlashcardResponse(BaseModel):
    id: int
    collection_id: int
    question: str
    answer: str
    is_favorite: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Dashboard Schemas
# ============================================================

class DashboardStats(BaseModel):
    total_collections: int = 0
    total_sources: int = 0
    total_chunks: int = 0
    total_questions: int = 0
    total_quizzes: int = 0
    total_generated: int = 0
    total_flashcards: int = 0
    duplicate_groups: int = 0
    average_quiz_score: Optional[float] = None


class RecentActivity(BaseModel):
    type: str  # source_added, quiz_taken, content_generated, etc.
    title: str
    description: Optional[str] = None
    timestamp: datetime
    collection_id: Optional[int] = None
    collection_name: Optional[str] = None


# ============================================================
# Export Schemas
# ============================================================

class ExportRequest(BaseModel):
    content_type: str = Field(
        ...,
        description="Type of content to export: generated_content, questions, quiz_results"
    )
    content_id: Optional[int] = Field(None, description="ID of specific content to export")
    collection_id: Optional[int] = Field(None, description="Collection ID for bulk export")
    title: Optional[str] = Field("Source2Study Export", description="Title for the export document")
    include_sources: bool = Field(True, description="Include source references")


# Forward reference update
CollectionDetail.model_rebuild()
