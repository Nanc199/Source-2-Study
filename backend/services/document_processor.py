"""
StudyMind AI - Document Processing Service
Handles extraction from PDF, DOCX, PPTX, Images, URLs, and YouTube.
"""

import os
import re
import json
import logging
import traceback
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes uploaded documents and extracts text content."""

    def __init__(self, db: Session):
        self.db = db

    def process_source(self, source_id: int) -> bool:
        """Main entry point: process a source by its ID."""
        from models import Source, ExtractedChunk
        
        source = self.db.query(Source).filter(Source.id == source_id).first()
        if not source:
            logger.error(f"Source {source_id} not found")
            return False

        source.status = "processing"
        self.db.commit()

        try:
            text = ""
            page_count = None

            if source.file_type == "pdf":
                text, page_count = self.extract_pdf(source.file_path)
            elif source.file_type == "docx":
                text, page_count = self.extract_docx(source.file_path)
            elif source.file_type in ("pptx", "ppt"):
                text, page_count = self.extract_pptx(source.file_path)
            elif source.file_type == "image":
                text = self.extract_image(source.file_path)
                page_count = 1
            elif source.file_type == "url":
                text = self.extract_url(source.url)
                page_count = 1
            elif source.file_type == "youtube":
                text = self.extract_youtube(source.url)
                page_count = 1
            else:
                raise ValueError(f"Unsupported file type: {source.file_type}")

            if not text or not text.strip():
                raise ValueError("No text could be extracted from this source")

            cleaned = self.clean_text(text)
            chunks = self.chunk_text(cleaned)

            # Delete old chunks for this source
            self.db.query(ExtractedChunk).filter(
                ExtractedChunk.source_id == source_id
            ).delete()

            self.store_chunks(source_id, source.collection_id, chunks)

            source.status = "completed"
            source.page_count = page_count
            source.error_message = None
            self.db.commit()

            # Generate embeddings
            try:
                self.generate_embeddings(source.collection_id, source_id)
            except Exception as e:
                logger.warning(f"Embedding generation failed for source {source_id}: {e}")

            return True

        except Exception as e:
            logger.error(f"Error processing source {source_id}: {traceback.format_exc()}")
            source.status = "failed"
            source.error_message = str(e)[:500]
            self.db.commit()
            return False

    def extract_pdf(self, file_path: str) -> Tuple[str, int]:
        """Extract text from PDF using PyMuPDF. Falls back to OCR for scanned PDFs."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF is required. Install with: pip install pymupdf")

        doc = fitz.open(file_path)
        page_count = len(doc)
        all_text = []

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")

            # If no text extracted, try OCR
            if not text.strip():
                try:
                    text = self._ocr_page_image(page)
                except Exception as e:
                    logger.warning(f"OCR failed for page {page_num + 1}: {e}")
                    text = ""

            if text.strip():
                all_text.append(f"[Page {page_num + 1}]\n{text}")

        doc.close()
        return "\n\n".join(all_text), page_count

    def _ocr_page_image(self, page) -> str:
        """OCR a PDF page by rendering it as an image."""
        try:
            import pytesseract
            from PIL import Image
            import io

            pix = page.get_pixmap(matrix=page.identity_matrix * 2)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            try:
                text = pytesseract.image_to_string(img)
                if text.strip():
                    return text
            except Exception as e:
                logger.info("Local OCR unavailable for scanned PDF page; using Gemini vision: %s", e)
            return self._extract_image_with_gemini(img)
        except Exception as e:
            logger.warning("Scanned PDF page OCR failed: %s", e)
            return ""

    def extract_docx(self, file_path: str) -> Tuple[str, int]:
        """Extract text from DOCX preserving headings and structure."""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("python-docx is required. Install with: pip install python-docx")

        doc = Document(file_path)
        all_text = []
        page_estimate = 1

        for para in doc.paragraphs:
            if not para.text.strip():
                continue
            style_name = para.style.name if para.style else ""
            if "Heading" in style_name:
                level = style_name.replace("Heading", "").strip() or "1"
                prefix = "#" * min(int(level) if level.isdigit() else 1, 4)
                all_text.append(f"\n{prefix} {para.text}\n")
            else:
                all_text.append(para.text)

        # Extract from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    all_text.append(row_text)

        full_text = "\n".join(all_text)
        page_estimate = max(1, len(full_text) // 3000)
        return full_text, page_estimate

    def extract_pptx(self, file_path: str) -> Tuple[str, int]:
        """Extract text from PPTX preserving slide numbers."""
        try:
            from pptx import Presentation
        except ImportError:
            raise ImportError("python-pptx is required. Install with: pip install python-pptx")

        prs = Presentation(file_path)
        all_text = []
        slide_count = len(prs.slides)

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_text = [f"[Slide {slide_num}]"]
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_text.append(text)
                if shape.has_table:
                    for row in shape.table.rows:
                        row_text = " | ".join(
                            cell.text.strip() for cell in row.cells if cell.text.strip()
                        )
                        if row_text:
                            slide_text.append(row_text)
            if len(slide_text) > 1:
                all_text.append("\n".join(slide_text))

            # Extract notes
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    all_text.append(f"[Slide {slide_num} Notes]\n{notes}")

        return "\n\n".join(all_text), slide_count

    def extract_image(self, file_path: str) -> str:
        """Extract text locally, with Gemini vision as a fallback when Tesseract is missing."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            from PIL import Image
            img = Image.open(file_path)
            return self._extract_image_with_gemini(img)

        img = Image.open(file_path)
        try:
            text = pytesseract.image_to_string(img)
            if text.strip():
                return text
        except Exception as e:
            logger.info("Local OCR unavailable; using Gemini vision: %s", e)
        text = self._extract_image_with_gemini(img)
        if not text.strip():
            raise ValueError("Could not extract readable text from this image.")
        return text

    def _extract_image_with_gemini(self, image) -> str:
        """Read text from an image using the configured multimodal Gemini model."""
        from config import settings
        if not settings.GEMINI_API_KEY:
            raise ValueError("Image OCR needs Tesseract installed or a configured Gemini API key.")
        from PIL import Image
        import io
        from google.genai import types
        from services.rag_service import RAGService

        image = image.convert("RGB")
        image.thumbnail((2048, 2048))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        prompt = (
            "Transcribe all readable text from this study image faithfully. "
            "Preserve headings, lists, equations, and table content as plain text. "
            "Do not summarize or add commentary."
        )
        parts = [prompt, types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/png")]
        return RAGService()._call_gemini(parts, max_output_tokens=4096, timeout_ms=40000)

    def extract_url(self, url: str) -> str:
        """Extract content from a webpage."""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("requests and beautifulsoup4 are required.")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        # Try to find main content
        main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main|article", re.I))
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def extract_youtube(self, url: str) -> str:
        """Extract transcript from YouTube video."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            raise ImportError("youtube-transcript-api is required.")

        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")

        try:
            # youtube-transcript-api 1.x uses an instance and returns snippet objects;
            # 0.x exposed get_transcript() and returned dictionaries.
            languages = ["hi", "en"]
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
                except Exception:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            else:
                api = YouTubeTranscriptApi()
                try:
                    transcript_list = api.fetch(video_id, languages=languages)
                except Exception:
                    transcript_list = api.fetch(video_id)
        except Exception as e:
            raise ValueError(
                "YouTube transcript unavailable. This video needs captions (auto-captions are okay) "
                f"and must be publicly accessible. Details: {e}"
            ) from e

        segments = []
        for entry in transcript_list:
            text = (entry.get("text", "") if isinstance(entry, dict) else getattr(entry, "text", "")).strip()
            if text:
                segments.append(text)

        return " ".join(segments)

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/)([a-zA-Z0-9_-]{11})",
            r"(?:shorts/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Normalize unicode
        text = text.replace("\u00a0", " ")
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')

        # Remove excessive whitespace but preserve paragraph breaks
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            line = re.sub(r"[ \t]+", " ", line.strip())
            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        return text.strip()

    def chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[Dict]:
        """Split text into overlapping chunks with metadata."""
        chunks = []
        # Try to split by paragraphs first
        paragraphs = text.split("\n\n")
        current_chunk = ""
        current_page = None
        chunk_index = 0

        for para in paragraphs:
            # Detect page markers
            page_match = re.match(r"\[Page (\d+)\]", para)
            slide_match = re.match(r"\[Slide (\d+)\]", para)
            if page_match:
                current_page = int(page_match.group(1))
            elif slide_match:
                current_page = int(slide_match.group(1))

            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "chunk_index": chunk_index,
                    "page_number": current_page,
                })
                chunk_index += 1
                # Keep overlap
                words = current_chunk.split()
                overlap_words = words[-overlap // 5:] if len(words) > overlap // 5 else []
                current_chunk = " ".join(overlap_words) + "\n\n" + para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "chunk_index": chunk_index,
                "page_number": current_page,
            })

        return chunks if chunks else [{"content": text[:chunk_size], "chunk_index": 0, "page_number": None}]

    def store_chunks(self, source_id: int, collection_id: int, chunks: List[Dict]):
        """Store extracted chunks in the database."""
        from models import ExtractedChunk

        for chunk_data in chunks:
            chunk = ExtractedChunk(
                source_id=source_id,
                collection_id=collection_id,
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data.get("page_number"),
                section_title=chunk_data.get("section_title"),
                metadata_json=chunk_data.get("metadata"),
            )
            self.db.add(chunk)
        self.db.commit()

    def generate_embeddings(self, collection_id: int, source_id: int = None):
        """Generate embeddings for chunks and store in ChromaDB."""
        from models import ExtractedChunk, Source
        from services.rag_service import RAGService

        rag = RAGService()
        
        query = self.db.query(ExtractedChunk).filter(
            ExtractedChunk.collection_id == collection_id
        )
        if source_id:
            query = query.filter(ExtractedChunk.source_id == source_id)
        
        chunks = query.all()
        if not chunks:
            return

        documents = []
        metadatas = []
        ids = []

        for chunk in chunks:
            source = self.db.query(Source).filter(Source.id == chunk.source_id).first()
            documents.append(chunk.content)
            metadatas.append({
                "source_id": chunk.source_id,
                "collection_id": chunk.collection_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number or 0,
                "source_filename": source.original_filename or source.filename or "Unknown",
                "source_type": source.file_type or "unknown",
            })
            ids.append(f"chunk_{chunk.id}")

        rag.add_documents(str(collection_id), documents, metadatas, ids)
