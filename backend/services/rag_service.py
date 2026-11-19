"""
StudyMind AI - RAG Service
Retrieval-Augmented Generation using ChromaDB and Google Gemini.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any

from config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded globals
_chroma_client = None
_embedding_function = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        os.makedirs(settings.CHROMA_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def _get_embedding_function():
    global _embedding_function
    if _embedding_function is None:
        from chromadb.utils import embedding_functions
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
    return _embedding_function


class RAGService:
    """RAG service for semantic search and AI-powered responses."""

    def __init__(self):
        # Generation reads SQL chunks and calls Gemini; load local embeddings only
        # when semantic search or vector writes actually need them.
        self.client = None
        self.embedding_fn = None

    def get_or_create_collection(self, collection_id: str):
        """Get or create a ChromaDB collection for a study collection."""
        if self.client is None:
            self.client = _get_chroma_client()
        if self.embedding_fn is None:
            self.embedding_fn = _get_embedding_function()
        return self.client.get_or_create_collection(
            name=f"collection_{collection_id}",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        collection_id: str,
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str],
    ):
        """Add document chunks to the vector store."""
        collection = self.get_or_create_collection(collection_id)
        
        # ChromaDB has a batch limit, process in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            collection.upsert(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
            )
        logger.info(f"Added {len(documents)} documents to collection {collection_id}")

    def search(
        self, collection_id: str, query: str, k: int = 5
    ) -> List[Dict[str, Any]]:
        """Semantic search for relevant document chunks."""
        collection = self.get_or_create_collection(collection_id)
        
        try:
            count = collection.count()
            if count == 0:
                return []
        except Exception:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                search_results.append({
                    "content": doc,
                    "metadata": meta,
                    "score": 1 - distance,  # Convert distance to similarity
                    "source_filename": meta.get("source_filename", "Unknown"),
                    "page_number": meta.get("page_number", 0),
                })

        return search_results

    def generate_response(
        self,
        collection_id: str,
        query: str,
        chat_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Generate an AI response using RAG."""
        if not settings.GEMINI_API_KEY:
            return {
                "content": "⚠️ **Gemini API key not configured.** Please add your GEMINI_API_KEY to the .env file to enable AI features. You can get an API key from https://makersuite.google.com/app/apikey",
                "sources": [],
            }

        # Search for relevant chunks
        search_results = self.search(collection_id, query, k=6)

        if not search_results:
            return {
                "content": "I couldn't find any relevant information in your uploaded documents. Please make sure you have uploaded and processed documents in this collection.",
                "sources": [],
            }

        # Build context from search results
        context_parts = []
        sources = []
        seen_sources = set()
        for r in search_results:
            context_parts.append(f"[Source: {r['source_filename']}, Page: {r['page_number']}]\n{r['content']}")
            source_key = f"{r['source_filename']}_{r['page_number']}"
            if source_key not in seen_sources:
                sources.append({
                    "filename": r["source_filename"],
                    "page_number": r["page_number"],
                    "relevance": round(r["score"], 3),
                })
                seen_sources.add(source_key)

        context = "\n\n---\n\n".join(context_parts)

        # Build chat history string
        history_str = ""
        if chat_history:
            for msg in chat_history[-6:]:  # Last 6 messages for context
                role = "Student" if msg.get("role") == "user" else "AI"
                history_str += f"{role}: {msg.get('content', '')}\n"

        prompt = f"""You are StudyMind AI, an intelligent study assistant. Answer the student's question based ONLY on the provided document context. Be accurate, helpful, and educational.

RULES:
1. Only use information from the provided context
2. If the context doesn't contain the answer, say so honestly
3. Reference specific sources when possible
4. Use clear formatting with headings, bullet points, and examples
5. Provide exam-oriented answers when relevant

DOCUMENT CONTEXT:
{context}

{f"PREVIOUS CONVERSATION:{chr(10)}{history_str}" if history_str else ""}

STUDENT'S QUESTION:
{query}

Provide a comprehensive, well-structured answer:"""

        try:
            response_text = self._call_gemini(prompt)
            return {
                "content": response_text,
                "sources": sources,
            }
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {
                "content": f"Error generating response: {str(e)}",
                "sources": sources,
            }

    def generate_content(
        self, collection_id: str, content_type: str, source_ids: Optional[List[int]] = None, db=None
    ) -> Any:
        """Generate study content using RAG."""
        if not settings.GEMINI_API_KEY:
            return {"error": "Gemini API key not configured. Add GEMINI_API_KEY to .env file."}

        # Get all chunks for context
        from models import ExtractedChunk, Source
        
        query = db.query(ExtractedChunk).filter(ExtractedChunk.collection_id == int(collection_id))
        if source_ids:
            query = query.filter(ExtractedChunk.source_id.in_(source_ids))
        chunks = query.order_by(ExtractedChunk.chunk_index).all()

        if not chunks:
            return {"error": "No content found. Please upload and process documents first."}

        # Keep prompts bounded. Large decks can otherwise send tens of thousands of
        # tokens and make even a short summary take several minutes.
        content_limit = 14000 if content_type == "short_summary" else 40000
        content_text = "\n\n".join(c.content for c in chunks[:50])[:content_limit]

        prompts = {
            "short_summary": f"""Based on the following study material, create a SHORT SUMMARY with:
- Key points in bullet format
- Important concepts highlighted
- Easy-to-understand language
- Organized by topic

CONTENT:
{content_text}

Generate a clear, concise bullet-point summary:""",

            "detailed_summary": f"""Based on the following study material, create a DETAILED SUMMARY with:
- Topic-wise explanations
- All important definitions
- Examples where available
- Clear headings and subheadings
- Comprehensive coverage of all topics

CONTENT:
{content_text}

Generate a detailed, well-structured summary:""",

            "short_answers": f"""Based on the following study material, generate SHORT ANSWER QUESTIONS (2-5 marks type).

For each question provide:
- The question
- A concise, exam-ready answer (50-100 words)

CONTENT:
{content_text}

Generate 15 short answer questions in this JSON format:
[{{"question": "...", "answer": "...", "marks": 3}}]""",

            "long_answers": f"""Based on the following study material, generate LONG ANSWER QUESTIONS (8-15 marks type).

For each question provide:
- The question
- A detailed answer with headings, explanations, and examples (200-400 words)

CONTENT:
{content_text}

Generate 8 long answer questions in this JSON format:
[{{"question": "...", "answer": "...", "marks": 10}}]""",

            "mcqs": f"""Based on the following study material, generate MULTIPLE CHOICE QUESTIONS.

For each question provide:
- The question
- 4 options (A, B, C, D)
- The correct answer
- A brief explanation

CONTENT:
{content_text}

Generate 20 MCQs in this JSON format:
[{{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A", "explanation": "..."}}]""",

            "important_questions": f"""Based on the following study material, identify the MOST IMPORTANT QUESTIONS that are likely to appear in exams.

Rank them by importance and relevance.

CONTENT:
{content_text}

Generate 20 important questions in this JSON format:
[{{"question": "...", "importance": "Very Important/Important/Moderate", "topic": "...", "type": "short/long"}}]""",

            "flashcards": f"""Based on the following study material, create FLASHCARDS for quick revision.

Each flashcard should have:
- A clear question on the front
- A concise answer on the back

CONTENT:
{content_text}

Generate 25 flashcards in this JSON format:
[{{"question": "...", "answer": "..."}}]""",

            "notes": f"""Based on the following study material, create CHAPTER-WISE NOTES.

Include:
- Clear headings and subheadings
- Key definitions
- Important points
- Examples
- Summary at the end of each topic

CONTENT:
{content_text}

Generate comprehensive study notes in a well-structured format:""",
        }

        prompt = prompts.get(content_type)
        if not prompt:
            return {"error": f"Unknown content type: {content_type}"}

        try:
            response_text = self._call_gemini(
                prompt,
                max_output_tokens=1200 if content_type == "short_summary" else 4096,
            )
            
            # Try to parse as JSON for structured types
            if content_type in ("short_answers", "long_answers", "mcqs", "important_questions", "flashcards"):
                try:
                    # Extract JSON from response
                    json_match = response_text
                    if "```json" in response_text:
                        json_match = response_text.split("```json")[1].split("```")[0]
                    elif "```" in response_text:
                        json_match = response_text.split("```")[1].split("```")[0]
                    parsed = json.loads(json_match.strip())
                    return {"content": parsed, "raw": response_text}
                except (json.JSONDecodeError, IndexError):
                    return {"content": response_text, "raw": response_text}
            
            return {"content": response_text}

        except Exception as e:
            logger.error(f"Content generation error: {e}")
            error_text = str(e)
            if any(marker in error_text.upper() for marker in (
                "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                "TIMED OUT", "TIMEOUT", "DEADLINE EXCEEDED",
            )):
                return {
                    "error": "Gemini is temporarily busy. Please wait a few seconds and try again.",
                    "status_code": 503,
                }
            return {"error": f"Failed to generate content: {error_text}"}

    def _call_gemini(
        self,
        prompt: Any,
        max_output_tokens: int = 4096,
        json_mode: bool = False,
        timeout_ms: int = 30000,
    ) -> str:
        """Call Google Gemini API."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("google-genai package is required. Install it with: pip install google-genai")

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )
        models = [settings.GEMINI_MODEL]
        if settings.GEMINI_FALLBACK_MODEL and settings.GEMINI_FALLBACK_MODEL not in models:
            models.append(settings.GEMINI_FALLBACK_MODEL)

        for index, model_name in enumerate(models):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json" if json_mode else None,
                    ),
                )
                if response.text:
                    if index:
                        logger.info("Gemini fallback model %s generated the response", model_name)
                    return response.text
                raise ValueError("Gemini returned an empty response")
            except Exception as e:
                error_text = str(e).upper()
                is_retryable_model_error = any(marker in error_text for marker in (
                    "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                    "TIMED OUT", "TIMEOUT", "DEADLINE EXCEEDED",
                    "404", "NOT_FOUND", "NOT FOUND", "UNSUPPORTED MODEL",
                ))
                if not is_retryable_model_error or index == len(models) - 1:
                    raise
                logger.warning("Gemini model %s is busy; trying fallback model %s", model_name, models[index + 1])

        raise ValueError("Gemini returned an empty response")

    def delete_collection_data(self, collection_id: str):
        """Delete all vector data for a collection."""
        try:
            _get_chroma_client().delete_collection(f"collection_{collection_id}")
        except Exception:
            pass

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(settings.EMBEDDING_MODEL)
            embeddings = model.encode(texts, show_progress_bar=False)
            return embeddings.tolist()
        except ImportError:
            # Fallback: use ChromaDB's embedding function
            if self.embedding_fn is None:
                self.embedding_fn = _get_embedding_function()
            return self.embedding_fn(texts)
