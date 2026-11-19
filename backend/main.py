"""
StudyMind AI - Main Application
FastAPI server entry point.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("studymind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Starting StudyMind AI...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_DIR, exist_ok=True)
    logger.info(f"Upload directory: {os.path.abspath(settings.UPLOAD_DIR)}")
    
    # Check Gemini API key
    if settings.GEMINI_API_KEY:
        logger.info("Gemini API key configured.")
    else:
        logger.warning("⚠️  GEMINI_API_KEY not set. AI features will be disabled.")
        logger.warning("   Add GEMINI_API_KEY to your .env file to enable AI features.")
    
    yield
    
    # Shutdown
    logger.info("StudyMind AI shutting down.")


# Create FastAPI app
app = FastAPI(
    title="StudyMind AI",
    description="AI-powered RAG-based Learning and Exam Preparation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again."},
    )


# Health check
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "StudyMind AI",
        "version": "1.0.0",
        "gemini_configured": bool(settings.GEMINI_API_KEY),
    }


# Register routers
from routers.auth_router import router as auth_router
from routers.collections_router import router as collections_router
from routers.sources_router import router as sources_router
from routers.chat_router import router as chat_router
from routers.study_router import router as study_router
from routers.questions_router import router as questions_router
from routers.quiz_router import router as quiz_router
from routers.dashboard_router import router as dashboard_router
from routers.export_router import router as export_router

app.include_router(auth_router)
app.include_router(collections_router)
app.include_router(sources_router)
app.include_router(chat_router)
app.include_router(study_router)
app.include_router(questions_router)
app.include_router(quiz_router)
app.include_router(dashboard_router)
app.include_router(export_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
