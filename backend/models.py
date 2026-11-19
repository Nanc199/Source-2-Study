"""
StudyMind AI - SQLAlchemy Models
Complete database models for the platform.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    sources = relationship("Source", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    generated_contents = relationship("GeneratedContent", back_populates="user", cascade="all, delete-orphan")
    extracted_questions = relationship("ExtractedQuestion", back_populates="user", cascade="all, delete-orphan")
    duplicate_groups = relationship("DuplicateGroup", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="user", cascade="all, delete-orphan")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="collections")
    sources = relationship("Source", back_populates="collection", cascade="all, delete-orphan")
    chunks = relationship("ExtractedChunk", back_populates="collection", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="collection", cascade="all, delete-orphan")
    generated_contents = relationship("GeneratedContent", back_populates="collection", cascade="all, delete-orphan")
    extracted_questions = relationship("ExtractedQuestion", back_populates="collection", cascade="all, delete-orphan")
    duplicate_groups = relationship("DuplicateGroup", back_populates="collection", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="collection", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="collection", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(512), nullable=True)
    original_filename = Column(String(512), nullable=True)
    file_type = Column(String(50), nullable=False)  # pdf, docx, pptx, image, url, youtube
    file_size = Column(Integer, nullable=True)  # in bytes
    file_path = Column(String(1024), nullable=True)
    url = Column(String(2048), nullable=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    collection = relationship("Collection", back_populates="sources")
    user = relationship("User", back_populates="sources")
    chunks = relationship("ExtractedChunk", back_populates="source", cascade="all, delete-orphan")
    extracted_questions = relationship("ExtractedQuestion", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sources_collection_status", "collection_id", "status"),
    )


class ExtractedChunk(Base):
    __tablename__ = "extracted_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(512), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    source = relationship("Source", back_populates="chunks")
    collection = relationship("Collection", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_source_index", "source_id", "chunk_index"),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Chat", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    collection = relationship("Collection", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    sources_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class GeneratedContent(Base):
    __tablename__ = "generated_contents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type = Column(String(50), nullable=False, index=True)
    # Types: short_summary, detailed_summary, short_answers, long_answers, mcqs, important_questions, flashcards, notes
    content_json = Column(JSON, nullable=False)
    source_ids_json = Column(JSON, nullable=True)
    title = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="generated_contents")
    collection = relationship("Collection", back_populates="generated_contents")

    __table_args__ = (
        Index("ix_generated_collection_type", "collection_id", "content_type"),
    )


class ExtractedQuestion(Base):
    __tablename__ = "extracted_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=True)  # short, long, mcq, etc.
    page_number = Column(Integer, nullable=True)
    year = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    source = relationship("Source", back_populates="extracted_questions")
    collection = relationship("Collection", back_populates="extracted_questions")
    user = relationship("User", back_populates="extracted_questions")
    group_memberships = relationship("DuplicateGroupMember", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_questions_collection_source", "collection_id", "source_id"),
    )


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_question = Column(Text, nullable=False)
    topic = Column(String(255), nullable=True)
    frequency = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    collection = relationship("Collection", back_populates="duplicate_groups")
    user = relationship("User", back_populates="duplicate_groups")
    members = relationship("DuplicateGroupMember", back_populates="group", cascade="all, delete-orphan")


class DuplicateGroupMember(Base):
    __tablename__ = "duplicate_group_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("duplicate_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("extracted_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Float, default=1.0, nullable=False)

    # Relationships
    group = relationship("DuplicateGroup", back_populates="members")
    question = relationship("ExtractedQuestion", back_populates="group_memberships")

    __table_args__ = (
        Index("ix_members_group_question", "group_id", "question_id", unique=True),
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    difficulty = Column(String(50), nullable=True)
    question_count = Column(Integer, nullable=False)
    score = Column(Float, nullable=True)
    total_marks = Column(Float, nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    questions_json = Column(JSON, nullable=False)
    answers_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="quiz_attempts")
    collection = relationship("Collection", back_populates="quiz_attempts")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="flashcards")
    collection = relationship("Collection", back_populates="flashcards")
