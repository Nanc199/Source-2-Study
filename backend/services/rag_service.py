"""
Source2Study - RAG Service
Retrieval-Augmented Generation using ChromaDB and Google Gemini.
High-speed, optimized inference strictly within the 30-second budget.
"""

import os
import time
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
    """RAG service for semantic search and fast, reliable AI-powered responses."""

    def __init__(self):
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
        self, collection_id: str, query: str, k: int = 4
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
                    "score": 1.0 - distance,
                    "source_filename": meta.get("source_filename", "Document"),
                    "page_number": meta.get("page_number", 0),
                })

        return search_results

    def generate_response(
        self,
        collection_id: str,
        query: str,
        chat_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Generate an AI response using RAG strictly within a 30-second budget."""
        t_start = time.time()

        if not settings.GEMINI_API_KEY:
            return {
                "content": "⚠️ **Gemini API key not configured.** Please add your GEMINI_API_KEY to the .env file to enable AI features.",
                "sources": [],
            }

        # 1. Search for relevant chunks (focused k=4)
        t_retrieval_start = time.time()
        search_results = self.search(collection_id, query, k=4)
        t_retrieval = time.time() - t_retrieval_start

        sources = []
        seen_sources = set()
        context_parts = []

        has_relevant_chunks = False
        if search_results:
            for r in search_results:
                # Include chunks with positive relevance
                if r["score"] > 0.15:
                    has_relevant_chunks = True
                    # Truncate overly long single chunks to 1200 chars
                    chunk_text = r["content"][:1200]
                    context_parts.append(f"[Source: {r['source_filename']}, Page: {r['page_number']}]\n{chunk_text}")
                    source_key = f"{r['source_filename']}_{r['page_number']}"
                    if source_key not in seen_sources:
                        sources.append({
                            "filename": r["source_filename"],
                            "page_number": r["page_number"],
                            "relevance": round(r["score"], 3),
                        })
                        seen_sources.add(source_key)

        context = "\n\n---\n\n".join(context_parts)

        # 2. Build concise conversation history (last 4 turns)
        history_str = ""
        if chat_history:
            for msg in chat_history[-4:]:
                role = "Student" if msg.get("role") == "user" else "AI"
                history_str += f"{role}: {msg.get('content', '')[:300]}\n"

        # 3. Construct prompt with honest document grounding
        if has_relevant_chunks:
            prompt = f"""You are Source2Study, an intelligent AI study assistant.
Answer the student's question accurately using the provided document context.

RULES:
1. Ground your response in the provided document context and cite specific sources where applicable.
2. If the context does not fully cover the answer, state honestly: "The uploaded materials don't specifically detail this point, but in standard academic terms..." and provide a concise, correct explanation.
3. Be clear, structured, and exam-oriented with concise headings and bullet points.
4. Keep the response focused and direct.

DOCUMENT CONTEXT:
{context}

{f"RECENT CHAT:{chr(10)}{history_str}" if history_str else ""}

STUDENT'S QUESTION:
{query}

Answer:"""
        else:
            prompt = f"""You are Source2Study, an intelligent AI study assistant.
The student has asked a question, but there are no specific matching sections in the uploaded materials for this collection.

RULES:
1. Begin by mentioning: "Note: This topic was not found in your uploaded documents for this collection."
2. Provide a clear, educational, and accurate answer to help the student learn the concept.
3. Use clear formatting, bullet points, and key definitions.

{f"RECENT CHAT:{chr(10)}{history_str}" if history_str else ""}

STUDENT'S QUESTION:
{query}

Answer:"""

        # 4. Generate response via Gemini with total 28-second deadline budget
        try:
            remaining_time = max(5000, int((28.0 - (time.time() - t_start)) * 1000))
            response_text = self._call_gemini(
                prompt,
                max_output_tokens=1500,
                timeout_ms=remaining_time,
            )
            total_dur = time.time() - t_start
            logger.info(f"⚡ [RAG Complete] Chat response generated in {total_dur:.2f}s (Retrieval: {t_retrieval:.2f}s)")
            return {
                "content": response_text,
                "sources": sources,
            }
        except Exception as e:
            total_dur = time.time() - t_start
            logger.error(f"Gemini API error after {total_dur:.2f}s: {e}")
            err_msg = str(e)
            if "DEADLINE" in err_msg.upper() or "TIMEOUT" in err_msg.upper():
                return {
                    "content": "The AI response timed out while generating. Please try asking a more specific question.",
                    "sources": sources,
                }
            return {
                "content": f"Error generating response: {err_msg}",
                "sources": sources,
            }

    def generate_content(
        self, collection_id: str, content_type: str, source_ids: Optional[List[int]] = None, db=None
    ) -> Any:
        """Generate study content using RAG within a 30-second budget."""
        t_start = time.time()

        if not settings.GEMINI_API_KEY:
            return {"error": "Gemini API key not configured. Add GEMINI_API_KEY to .env file."}

        from models import ExtractedChunk
        
        query = db.query(ExtractedChunk).filter(ExtractedChunk.collection_id == int(collection_id))
        if source_ids:
            query = query.filter(ExtractedChunk.source_id.in_(source_ids))
        chunks = query.order_by(ExtractedChunk.chunk_index).all()

        if not chunks:
            return {"error": "No content found in this collection. Please upload study materials first."}

        # Full document coverage: Ensure start, middle, and end of document are all included
        total_chunks = len(chunks)
        total_chars = sum(len(c.content) for c in chunks)

        if total_chars <= 65000:
            # Whole document fits within context window
            content_text = "\n\n".join(c.content for c in chunks)
        else:
            # For exceptionally lengthy documents, ensure uniform coverage across all sections
            # Sample up to 45 chunks evenly distributed from chunk 0 to the final chunk
            step = (total_chunks - 1) / 44.0 if total_chunks > 45 else 1.0
            sampled_indices = sorted(list(set(int(round(i * step)) for i in range(min(45, total_chunks)))))
            sampled_chunks = [chunks[idx] for idx in sampled_indices if idx < total_chunks]
            content_text = "\n\n".join(c.content for c in sampled_chunks)[:65000]

        prompts = {
            "short_summary": f"""You are an expert academic educator. Provide a comprehensive yet concise EXECUTIVE SHORT SUMMARY of the study material below.

CRITICAL REQUIREMENTS:
- Cover ALL key concepts, essential definitions, fundamental facts, core processes, and conclusions from the ENTIRE document (from the first topic to the final section).
- Do NOT artificially truncate or omit important content to meet an arbitrary word count limit.
- Group the summary into clear topic-wise sections using Markdown headings (`### Section Name`).
- Use structured bullet points highlighting essential terminology, key formulas, and principles.
- Conclude with a 'Key Takeaways & Core Conclusions' section.
- Output clean, professional, readable Markdown notes.

STUDY MATERIAL:
{content_text}

Executive Short Summary:""",

            "detailed_summary": f"""You are an expert academic professor. Provide a thorough, comprehensive, and exhaustive DETAILED SUMMARY of the study material below.

CRITICAL REQUIREMENTS:
- Complete document coverage: Walk through the entire document in logical sequence, covering all major chapters, topics, and subtopics from start to finish.
- Do NOT stop halfway through the document or omit later sections and concluding chapters.
- Explain each major concept sufficiently with clear principles, step-by-step mechanisms, and relevant examples.
- Explicitly preserve and format all definitions, mathematical equations, symbols, formulas, and technical classifications.
- Structure using clear hierarchical Markdown headings (`## Chapter / Major Unit`, `### Topic / Subtopic`).
- Include a dedicated 'Formulas, Definitions & Key Equations Reference' section and a 'Summary of Conclusions'.
- Do NOT impose an arbitrary word limit that compromises depth or completeness.

STUDY MATERIAL:
{content_text}

Comprehensive Detailed Summary:""",

            "short_answers": f"""Based on the study material below, generate 10 SHORT ANSWER QUESTIONS (2-5 marks exam type) covering the entire document.
For each question provide a concise, exam-ready answer (50-80 words).

CONTENT:
{content_text}

Return JSON in this format:
[{{"question": "...", "answer": "...", "marks": 3}}]""",

            "long_answers": f"""Based on the study material below, generate 5 LONG ANSWER QUESTIONS (8-10 marks exam type) spanning major sections of the document.
For each question provide a detailed answer with headings, points, and explanations.

CONTENT:
{content_text}

Return JSON in this format:
[{{"question": "...", "answer": "...", "marks": 8}}]""",

            "mcqs": f"""Based on the study material below, generate 10 high-quality MULTIPLE CHOICE QUESTIONS covering key concepts from across the entire document.
For each question provide:
- The question
- 4 clear options labeled A, B, C, D
- The correct answer letter (e.g. "A", "B", "C", or "D")
- A brief explanation

CONTENT:
{content_text}

Return JSON in this format:
[{{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_answer": "A", "explanation": "..."}}]""",

            "important_questions": f"""Based on the study material below, identify 12 MOST IMPORTANT EXAM QUESTIONS covering all major topics.
Rank them by importance.

CONTENT:
{content_text}

Return JSON in this format:
[{{"question": "...", "importance": "Very Important/Important", "topic": "...", "type": "short/long"}}]""",

            "flashcards": f"""Based on the study material below, create 15 FLASHCARDS for quick revision covering key concepts across the document.
Each flashcard must have a question on the front and concise answer on the back.

CONTENT:
{content_text}

Return JSON in this format:
[{{"question": "...", "answer": "..."}}]""",

            "notes": f"""Based on the study material below, create structured CHAPTER-WISE NOTES covering all topics.
Include headings, key concepts, formulas, and summary points.

CONTENT:
{content_text}

Notes:""",
        }

        prompt = prompts.get(content_type)
        if not prompt:
            return {"error": f"Unknown content type: {content_type}"}

        try:
            tokens_budget = 3000 if content_type == "short_summary" else (4096 if content_type in ("detailed_summary", "notes") else 2500)
            remaining_time = max(5000, int((28.0 - (time.time() - t_start)) * 1000))
            response_text = self._call_gemini(
                prompt,
                max_output_tokens=tokens_budget,
                timeout_ms=remaining_time,
            )
            
            # Parse structured JSON responses
            if content_type in ("short_answers", "long_answers", "mcqs", "important_questions", "flashcards"):
                try:
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
            total_dur = time.time() - t_start
            logger.error(f"Content generation error after {total_dur:.2f}s: {e}")
            error_text = str(e)
            if any(marker in error_text.upper() for marker in (
                "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                "TIMED OUT", "TIMEOUT", "DEADLINE EXCEEDED",
            )):
                return {
                    "error": "Gemini AI is temporarily busy. Please wait a few seconds and try again.",
                    "status_code": 503,
                }
            return {"error": f"Failed to generate content: {error_text}"}

    def _call_gemini(
        self,
        prompt: Any,
        max_output_tokens: int = 1500,
        json_mode: bool = False,
        timeout_ms: int = 28000,
    ) -> str:
        """Call Google Gemini API with smart per-attempt timeouts within a strict budget."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("google-genai package is required. Install it with: pip install google-genai")

        overall_deadline = time.time() + (timeout_ms / 1000.0)

        # Primary fast model with proven low latency, followed by reliable fallback
        models = [settings.GEMINI_MODEL]
        if settings.GEMINI_FALLBACK_MODEL and settings.GEMINI_FALLBACK_MODEL not in models:
            models.append(settings.GEMINI_FALLBACK_MODEL)
        # Ensure a 3rd fast fallback in case primary or secondary is unavailable
        tertiary_fallback = "gemini-3.5-flash-lite"
        if tertiary_fallback not in models:
            models.append(tertiary_fallback)

        last_error = None

        for index, model_name in enumerate(models):
            time_left = overall_deadline - time.time()
            if time_left <= 3.0:
                logger.warning(f"Insufficient time remaining ({time_left:.2f}s) to attempt model {model_name}")
                break

            # Allocate up to 16s for the first attempt, leaving ample time for fallback
            attempt_timeout = min(int(time_left * 1000), 16000 if index == 0 else int(time_left * 1000))

            t_call_start = time.time()
            try:
                client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(timeout=attempt_timeout),
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        top_p=0.85,
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json" if json_mode else None,
                    ),
                )
                dur = time.time() - t_call_start
                if response.text and response.text.strip():
                    logger.info(f"⚡ [Gemini Latency] Model '{model_name}' succeeded in {dur:.2f}s")
                    return response.text.strip()
                raise ValueError(f"Gemini model '{model_name}' returned empty response text")

            except Exception as e:
                dur = time.time() - t_call_start
                last_error = e
                err_str = str(e).upper()
                logger.warning(f"Gemini model '{model_name}' failed in {dur:.2f}s: {e}")

                is_retryable = any(m in err_str for m in (
                    "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                    "TIMED OUT", "TIMEOUT", "DEADLINE EXCEEDED",
                    "404", "NOT_FOUND", "NOT FOUND", "REMOTE DISCONNECTED",
                ))

                if not is_retryable or index == len(models) - 1:
                    raise e

        if last_error:
            raise last_error
        raise ValueError("Failed to obtain response from Gemini models within time limit.")

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
            if self.embedding_fn is None:
                self.embedding_fn = _get_embedding_function()
            return self.embedding_fn(texts)
