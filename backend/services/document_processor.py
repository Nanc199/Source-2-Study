"""
Source2Study - Document Processing Service
Handles extraction from PDF (including scanned/OCR), DOCX, PPTX, Images (OCR), URLs (SSRF-protected), and YouTube.
"""

import os
import re
import json
import logging
import traceback
import ipaddress
import socket
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from config import settings

logger = logging.getLogger(__name__)


def configure_tesseract():
    """Ensure pytesseract uses the configured or discovered Tesseract binary."""
    try:
        import pytesseract
        cmd = settings.TESSERACT_CMD
        if cmd and os.path.isfile(cmd):
            pytesseract.pytesseract.tesseract_cmd = cmd
    except Exception as e:
        logger.debug(f"Pytesseract configuration skipped: {e}")


configure_tesseract()


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
        """Extract text from PDF using PyMuPDF. Automatically applies OCR to scanned pages."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF is required. Install with: pip install pymupdf")

        doc = fitz.open(file_path)
        page_count = len(doc)
        all_text = []

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text").strip()

            # If page text is very sparse or missing, page is likely a scanned document or image
            if len(text) < 40:
                try:
                    ocr_text = self._ocr_page_image(page)
                    if ocr_text and len(ocr_text.strip()) > len(text):
                        text = ocr_text.strip()
                except Exception as e:
                    logger.warning(f"OCR failed for page {page_num + 1}: {e}")

            if text.strip():
                all_text.append(f"[Page {page_num + 1}]\n{text}")

        doc.close()
        return "\n\n".join(all_text), page_count

    def _ocr_page_image(self, page) -> str:
        """OCR a PDF page by rendering it as a high-resolution image."""
        try:
            import pytesseract
            from PIL import Image
            import io

            configure_tesseract()

            # Render at 150 DPI for sharp OCR recognition
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            try:
                text = pytesseract.image_to_string(img)
                if text and text.strip():
                    return text.strip()
            except Exception as e:
                logger.info("Local Tesseract OCR attempt failed: %s; trying Gemini fallback", e)

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
        """Extract text locally using Tesseract OCR, with Gemini vision fallback."""
        try:
            import pytesseract
            from PIL import Image

            configure_tesseract()

            img = Image.open(file_path)
            try:
                text = pytesseract.image_to_string(img)
                if text and text.strip():
                    return text.strip()
            except Exception as e:
                logger.info("Local OCR failed on image: %s; trying Gemini vision", e)

            return self._extract_image_with_gemini(img)
        except Exception as e:
            logger.warning("Image extraction failed: %s", e)
            raise ValueError(f"Could not extract readable text from image: {e}")

    def _extract_image_with_gemini(self, image) -> str:
        """Read text from an image using the configured multimodal Gemini model."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("Local OCR could not read the image and GEMINI_API_KEY is not configured.")

        import io
        from google.genai import types
        from services.rag_service import RAGService

        image = image.convert("RGB")
        image.thumbnail((2048, 2048))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        prompt = (
            "Transcribe all readable text from this study image faithfully. "
            "Preserve headings, question numbers, options, equations, and tables as plain text. "
            "Do not summarize or add commentary."
        )
        parts = [prompt, types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/png")]
        return RAGService()._call_gemini(parts, max_output_tokens=4096, timeout_ms=40000)

    @staticmethod
    def validate_safe_url(raw_url: str) -> str:
        """Validate URL scheme and protect against Server-Side Request Forgery (SSRF)."""
        if not raw_url or not isinstance(raw_url, str):
            raise ValueError("URL cannot be empty.")

        url = raw_url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP and HTTPS URLs are permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: missing domain hostname.")

        # Block localhost and common loopback/internal hosts
        blocked_hosts = {
            "localhost", "127.0.0.1", "0.0.0.0", "::1",
            "metadata.google.internal", "instance-data",
        }
        if hostname.lower() in blocked_hosts or hostname.lower().endswith(".local") or hostname.lower().endswith(".internal"):
            raise ValueError("Access to internal, local, or private network hosts is strictly prohibited.")

        # Resolve hostname to IP to protect against SSRF and private ranges
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise ValueError(f"Could not resolve host '{hostname}'. Please check that the URL is correct.") from e

        for entry in addr_info:
            ip_str = entry[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_multicast
                    or ip.is_reserved
                    or ip.is_unspecified
                ):
                    raise ValueError(
                        f"Access to private or local network address ({ip_str}) is prohibited."
                    )
            except ValueError as err:
                if "prohibited" in str(err):
                    raise
                continue

        return url

    def extract_url(self, raw_url: str) -> str:
        """Safely fetch and extract study text from a webpage."""
        import requests
        from bs4 import BeautifulSoup

        current_url = self.validate_safe_url(raw_url)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Follow redirects with SSRF validation on every step
        max_redirects = 5
        session = requests.Session()
        html_text = ""

        try:
            for _ in range(max_redirects):
                resp = session.get(
                    current_url,
                    headers=headers,
                    timeout=20,
                    allow_redirects=False,
                    stream=True,
                )

                if resp.is_redirect or resp.is_permanent_redirect or 300 <= resp.status_code < 400:
                    location = resp.headers.get("Location")
                    if not location:
                        break
                    next_url = urljoin(current_url, location)
                    current_url = self.validate_safe_url(next_url)
                    continue

                resp.raise_for_status()

                content_type = resp.headers.get("Content-Type", "").lower()
                if content_type and not ("text" in content_type or "html" in content_type or "xml" in content_type):
                    raise ValueError(f"URL returned non-textual content type: {content_type}")

                max_bytes = 15 * 1024 * 1024
                content_bytes = bytearray()
                for chunk in resp.iter_content(chunk_size=65536):
                    content_bytes.extend(chunk)
                    if len(content_bytes) > max_bytes:
                        raise ValueError("Webpage exceeds the maximum download limit of 15 MB.")

                html_text = content_bytes.decode(resp.encoding or "utf-8", errors="replace")
                break
            else:
                raise ValueError("Too many redirects encountered while accessing this webpage.")

        except requests.exceptions.Timeout:
            raise ValueError("Webpage request timed out after 20 seconds. The server might be slow or blocking requests.")
        except requests.exceptions.SSLError as e:
            raise ValueError(f"SSL certificate validation failed: {e}")
        except requests.exceptions.ConnectionError:
            raise ValueError("Could not connect to the webpage. Please verify the URL is valid and publicly accessible.")
        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, "status_code", "error")
            raise ValueError(f"Webpage returned HTTP status code {status_code}. The page may require login or permission.")

        soup = BeautifulSoup(html_text, "html.parser")

        # Capture title
        page_title = ""
        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()

        # Remove clutter
        for tag in soup.find_all([
            "script", "style", "nav", "footer", "header", "aside", "iframe",
            "noscript", "svg", "form", "button", "dialog"
        ]):
            tag.decompose()

        for el in soup.select(".nav, .navbar, .footer, .header, .cookie-banner, .advertisement, .ad, #cookie-notice"):
            el.decompose()

        # Find main content body
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find("div", id=re.compile(r"content|main|article|body", re.I))
            or soup.find("div", class_=re.compile(r"content|main|article|post", re.I))
            or soup.body
        )

        if not main:
            main = soup

        lines = []
        if page_title:
            lines.append(f"# {page_title}\n")

        for elem in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote", "pre", "table"]):
            if elem.name in ("h1", "h2", "h3", "h4"):
                level = elem.name[1]
                t = elem.get_text(strip=True)
                if t:
                    lines.append(f"\n{'#' * int(level)} {t}\n")
            elif elem.name == "li":
                t = elem.get_text(strip=True)
                if t:
                    lines.append(f"• {t}")
            elif elem.name == "table":
                rows = []
                for tr in elem.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if cells:
                        rows.append(" | ".join(cells))
                if rows:
                    lines.append("\n" + "\n".join(rows) + "\n")
            else:
                t = elem.get_text(strip=True)
                if t:
                    lines.append(t)

        extracted = "\n".join(lines).strip()
        if not extracted or len(extracted) < 50:
            extracted = main.get_text(separator="\n", strip=True)

        cleaned = re.sub(r"\n{3,}", "\n\n", extracted).strip()
        if len(cleaned) < 40:
            raise ValueError(
                "Could not extract readable study text from this webpage. "
                "The page may require JavaScript or authentication."
            )

        return cleaned

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
        text = text.replace("\u00a0", " ")
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')

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
        paragraphs = text.split("\n\n")
        current_chunk = ""
        current_page = None
        chunk_index = 0

        for para in paragraphs:
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
                "source_filename": source.original_filename if source else "Unknown",
                "source_type": source.file_type if source else "unknown",
            })
            ids.append(f"chunk_{chunk.id}")

        rag.add_documents(str(collection_id), documents, metadatas, ids)
