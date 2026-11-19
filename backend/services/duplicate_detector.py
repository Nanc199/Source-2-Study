"""
StudyMind AI - Duplicate Question Detector
The signature feature: semantic duplicate detection across question papers.
"""

import re
import json
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from config import settings

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Advanced AI-powered duplicate question detection system."""

    def __init__(self, db: Session):
        self.db = db
        self._embedding_model = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except ImportError:
                raise ImportError("sentence-transformers is required for duplicate detection.")
        return self._embedding_model

    def extract_questions_from_source(self, source_id: int, user_id: int) -> List[Dict]:
        """Extract individual questions from a source document."""
        from models import Source, ExtractedChunk, ExtractedQuestion

        source = self.db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return []

        chunks = (
            self.db.query(ExtractedChunk)
            .filter(ExtractedChunk.source_id == source_id)
            .order_by(ExtractedChunk.chunk_index)
            .all()
        )

        if not chunks:
            return []

        full_text = "\n\n".join([c.content for c in chunks])
        year = self._extract_year(source.original_filename or source.filename or "")

        # Extract questions using multiple methods
        questions = []
        
        # Method 1: Pattern-based extraction
        pattern_questions = self._extract_by_patterns(full_text)
        questions.extend(pattern_questions)

        # Method 2: Question mark-based extraction
        qmark_questions = self._extract_by_question_marks(full_text)
        for q in qmark_questions:
            if not any(self._quick_similar(q, eq) for eq in questions):
                questions.append(q)

        # Method 3: AI-based extraction (if API key available)
        if settings.GEMINI_API_KEY and len(questions) < 5:
            try:
                ai_questions = self._extract_by_ai(full_text)
                for q in ai_questions:
                    if not any(self._quick_similar(q, eq) for eq in questions):
                        questions.append(q)
            except Exception as e:
                logger.warning(f"AI question extraction failed: {e}")

        # Store extracted questions
        stored = []
        for q_text in questions:
            q_text = q_text.strip()
            if len(q_text) < 10 or len(q_text) > 2000:
                continue

            normalized = self.normalize_question(q_text)
            if len(normalized) < 5:
                continue

            # Check for existing identical question from same source
            existing = (
                self.db.query(ExtractedQuestion)
                .filter(
                    ExtractedQuestion.source_id == source_id,
                    ExtractedQuestion.normalized_text == normalized,
                )
                .first()
            )
            if existing:
                continue

            # Detect question type
            q_type = self._detect_question_type(q_text)
            page_num = self._find_page_number(q_text, chunks)

            eq = ExtractedQuestion(
                source_id=source_id,
                collection_id=source.collection_id,
                user_id=user_id,
                question_text=q_text,
                normalized_text=normalized,
                question_type=q_type,
                page_number=page_num,
                year=year,
            )
            self.db.add(eq)
            stored.append(eq)

        self.db.commit()
        return stored

    def _extract_by_patterns(self, text: str) -> List[str]:
        """Extract questions using numbering patterns."""
        questions = []
        patterns = [
            r'(?:^|\n)\s*(?:Q\.?\s*)?(\d{1,3})\s*[\.\)\]]\s*(.+?)(?=(?:\n\s*(?:Q\.?\s*)?\d{1,3}\s*[\.\)\]])|$)',
            r'(?:^|\n)\s*(?:Question)\s*(\d{1,3})\s*[:\.\)]\s*(.+?)(?=(?:\nQuestion\s*\d)|$)',
            r'(?:^|\n)\s*\(([a-zA-Z])\)\s*(.+?)(?=(?:\n\s*\([a-zA-Z]\))|$)',
            r'(?:^|\n)\s*([ivxIVX]+)\s*[\.\)]\s*(.+?)(?=(?:\n\s*[ivxIVX]+\s*[\.\)])|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
            for match in matches:
                q_text = match[-1].strip() if isinstance(match, tuple) else match.strip()
                q_text = re.sub(r'\s+', ' ', q_text)
                if len(q_text) > 15 and ('?' in q_text or any(
                    kw in q_text.lower() for kw in
                    ['explain', 'define', 'describe', 'what', 'how', 'why', 'discuss',
                     'compare', 'differentiate', 'list', 'enumerate', 'write', 'state',
                     'derive', 'prove', 'solve', 'calculate', 'illustrate']
                )):
                    questions.append(q_text)

        return questions

    def _extract_by_question_marks(self, text: str) -> List[str]:
        """Extract sentences that end with question marks."""
        questions = []
        sentences = re.split(r'(?<=[.?!])\s+', text)
        current = ""

        for sent in sentences:
            current += " " + sent if current else sent
            if '?' in sent:
                q = current.strip()
                if len(q) > 15:
                    questions.append(q)
                current = ""
            elif len(current) > 500:
                current = ""

        return questions

    def _extract_by_ai(self, text: str) -> List[str]:
        """Use Gemini to extract questions from text."""
        from services.rag_service import RAGService
        rag = RAGService()

        prompt = f"""Extract ALL exam/test questions from the following text. 
Return ONLY the questions, one per line. Do not include answers.
Include questions that start with action words like Explain, Define, Describe, Compare, etc.

TEXT:
{text[:8000]}

QUESTIONS (one per line):"""

        try:
            response = rag._call_gemini(prompt)
            lines = response.strip().split('\n')
            questions = []
            for line in lines:
                line = line.strip()
                line = re.sub(r'^\d+[\.\)]\s*', '', line)
                line = re.sub(r'^[-•]\s*', '', line)
                if len(line) > 15:
                    questions.append(line)
            return questions
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
            return []

    def _quick_similar(self, q1: str, q2: str) -> bool:
        """Quick check if two questions are very similar (exact/near-exact)."""
        n1 = self.normalize_question(q1)
        n2 = self.normalize_question(q2)
        if n1 == n2:
            return True
        # Check word overlap
        w1 = set(n1.split())
        w2 = set(n2.split())
        if not w1 or not w2:
            return False
        overlap = len(w1 & w2) / max(len(w1), len(w2))
        return overlap > 0.9

    def normalize_question(self, text: str) -> str:
        """Normalize question text for comparison."""
        text = text.lower().strip()
        # Remove question numbers
        text = re.sub(r'^(?:q\.?\s*)?(?:\d{1,3})\s*[\.\)\]:\s]+', '', text)
        text = re.sub(r'^(?:question)\s*\d*\s*[:\.\)]*\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\([a-zA-Z]\)\s*', '', text)
        # Remove marks indicators
        text = re.sub(r'\[\s*\d+\s*(?:marks?|m)\s*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\s*\d+\s*(?:marks?|m)\s*\)', '', text, flags=re.IGNORECASE)
        # Normalize whitespace and punctuation
        text = re.sub(r'[^\w\s?]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _detect_question_type(self, text: str) -> str:
        """Detect the type of question."""
        text_lower = text.lower()
        marks_match = re.search(r'(\d+)\s*marks?', text_lower)
        if marks_match:
            marks = int(marks_match.group(1))
            if marks <= 5:
                return "short"
            else:
                return "long"

        short_keywords = ['define', 'state', 'list', 'name', 'what is', 'what are', 'write short note']
        long_keywords = ['explain in detail', 'discuss', 'elaborate', 'describe in detail', 'compare and contrast']

        for kw in long_keywords:
            if kw in text_lower:
                return "long"
        for kw in short_keywords:
            if kw in text_lower:
                return "short"

        return "medium"

    def _find_page_number(self, question: str, chunks) -> Optional[int]:
        """Find which page a question appears on."""
        for chunk in chunks:
            if question[:50] in chunk.content:
                return chunk.page_number
        return None

    def _extract_year(self, filename: str) -> Optional[str]:
        """Extract year from filename."""
        match = re.search(r'(20\d{2})', filename)
        return match.group(1) if match else None

    def detect_duplicates(
        self,
        collection_id: int,
        user_id: int,
        similarity_threshold: float = None,
        use_llm_verification: bool = True,
    ) -> Dict[str, Any]:
        """Main duplicate detection pipeline."""
        from models import ExtractedQuestion, DuplicateGroup, DuplicateGroupMember, Source

        if similarity_threshold is None:
            similarity_threshold = settings.SIMILARITY_THRESHOLD

        # Step 1: Extract questions from all sources in collection
        sources = (
            self.db.query(Source)
            .filter(Source.collection_id == collection_id, Source.status == "completed")
            .all()
        )

        for source in sources:
            existing_count = (
                self.db.query(ExtractedQuestion)
                .filter(ExtractedQuestion.source_id == source.id)
                .count()
            )
            if existing_count == 0:
                self.extract_questions_from_source(source.id, user_id)

        # Step 2: Get all questions
        questions = (
            self.db.query(ExtractedQuestion)
            .filter(ExtractedQuestion.collection_id == collection_id)
            .all()
        )

        if len(questions) < 2:
            return {
                "total_documents": len(sources),
                "total_questions": len(questions),
                "unique_questions": len(questions),
                "duplicate_questions": 0,
                "duplicate_percentage": 0.0,
                "groups_created": 0,
                "most_frequent_questions": [],
            }

        # Step 3: Generate embeddings
        texts = [q.normalized_text for q in questions]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings)

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings_normalized = embeddings / norms

        # Step 4: Calculate similarity matrix
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)

        # Step 5: Group duplicates using Union-Find
        n = len(questions)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Find pairs above threshold
        ambiguous_pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                sim = similarity_matrix[i][j]
                if sim >= similarity_threshold:
                    # High confidence duplicate
                    union(i, j)
                elif sim >= (similarity_threshold - 0.10) and use_llm_verification:
                    # Ambiguous - needs LLM verification
                    ambiguous_pairs.append((i, j, sim))

        # Step 6: LLM verification for ambiguous pairs
        if ambiguous_pairs and settings.GEMINI_API_KEY:
            for i, j, sim in ambiguous_pairs[:20]:  # Limit LLM calls
                try:
                    is_dup = self._llm_verify_duplicate(
                        questions[i].question_text,
                        questions[j].question_text,
                    )
                    if is_dup:
                        union(i, j)
                except Exception as e:
                    logger.warning(f"LLM verification failed: {e}")

        # Step 7: Build groups
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)

        # Step 8: Clear old groups for this collection
        old_groups = (
            self.db.query(DuplicateGroup)
            .filter(DuplicateGroup.collection_id == collection_id)
            .all()
        )
        for g in old_groups:
            self.db.delete(g)
        self.db.flush()

        # Step 9: Create new groups
        groups_created = 0
        duplicate_count = 0

        for representative_idx, member_indices in groups.items():
            if len(member_indices) < 1:
                continue

            # Pick the best canonical question (longest, most complete)
            member_questions = [questions[i] for i in member_indices]
            canonical = max(member_questions, key=lambda q: len(q.question_text))

            # Determine topic using first few words
            topic = self._infer_topic(canonical.question_text)

            group = DuplicateGroup(
                collection_id=collection_id,
                user_id=user_id,
                canonical_question=canonical.question_text,
                topic=topic,
                frequency=len(member_indices),
            )
            self.db.add(group)
            self.db.flush()

            for idx in member_indices:
                q = questions[idx]
                sim = float(similarity_matrix[representative_idx][idx]) if idx != representative_idx else 1.0
                member = DuplicateGroupMember(
                    group_id=group.id,
                    question_id=q.id,
                    similarity_score=sim,
                )
                self.db.add(member)

            if len(member_indices) > 1:
                duplicate_count += len(member_indices) - 1

            groups_created += 1

        self.db.commit()

        # Build stats
        unique_count = groups_created
        total_q = len(questions)
        dup_pct = (duplicate_count / total_q * 100) if total_q > 0 else 0

        # Most frequent questions
        most_frequent = (
            self.db.query(DuplicateGroup)
            .filter(DuplicateGroup.collection_id == collection_id)
            .order_by(DuplicateGroup.frequency.desc())
            .limit(10)
            .all()
        )

        return {
            "total_documents": len(sources),
            "total_questions": total_q,
            "unique_questions": unique_count,
            "duplicate_questions": duplicate_count,
            "duplicate_percentage": round(dup_pct, 1),
            "groups_created": groups_created,
            "most_frequent_questions": [
                {
                    "question": g.canonical_question,
                    "frequency": g.frequency,
                    "topic": g.topic,
                }
                for g in most_frequent
            ],
        }

    def _llm_verify_duplicate(self, q1: str, q2: str) -> bool:
        """Use LLM to verify if two questions are semantically equivalent."""
        from services.rag_service import RAGService
        rag = RAGService()

        prompt = f"""Determine if these two exam questions are asking essentially the SAME thing (just worded differently) or if they are asking DIFFERENT things.

IMPORTANT RULES:
- "Define Machine Learning" and "What do you mean by Machine Learning?" → SAME (just different wording)
- "Explain supervised learning" and "Explain unsupervised learning" → DIFFERENT (different topics)
- "Explain AI" and "Explain applications of AI" → DIFFERENT (one is general, other asks specifically about applications)
- "What is AI?" and "Define Artificial Intelligence" → SAME

Question 1: {q1}
Question 2: {q2}

Answer ONLY with "SAME" or "DIFFERENT":"""

        try:
            response = rag._call_gemini(prompt).strip().upper()
            return "SAME" in response
        except Exception:
            return False

    def _infer_topic(self, question: str) -> str:
        """Infer topic from question text."""
        question_lower = question.lower()
        # Simple keyword-based topic detection
        topic_keywords = {
            "Artificial Intelligence": ["artificial intelligence", " ai ", "ai?"],
            "Machine Learning": ["machine learning", " ml "],
            "Deep Learning": ["deep learning", "neural network", "cnn", "rnn"],
            "Data Structures": ["data structure", "linked list", "tree", "graph", "stack", "queue"],
            "Algorithms": ["algorithm", "sorting", "searching", "complexity"],
            "Database": ["database", "sql", "normalization", "dbms", "relational"],
            "Operating System": ["operating system", " os ", "process", "thread", "scheduling"],
            "Computer Network": ["network", "tcp", "ip", "protocol", "osi"],
            "Software Engineering": ["software engineering", "sdlc", "agile", "testing"],
        }

        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in question_lower:
                    return topic

        # Default: use first few significant words
        words = re.sub(r'[^\w\s]', '', question).split()
        significant = [w for w in words if len(w) > 3 and w.lower() not in
                       {'what', 'explain', 'define', 'describe', 'discuss', 'with', 'from', 'that', 'this', 'have', 'been'}]
        return " ".join(significant[:3]).title() if significant else "General"

    def get_stats(self, collection_id: int) -> Dict:
        """Get duplicate detection statistics."""
        from models import ExtractedQuestion, DuplicateGroup, Source

        sources = self.db.query(Source).filter(
            Source.collection_id == collection_id, Source.status == "completed"
        ).count()

        total_q = self.db.query(ExtractedQuestion).filter(
            ExtractedQuestion.collection_id == collection_id
        ).count()

        groups = self.db.query(DuplicateGroup).filter(
            DuplicateGroup.collection_id == collection_id
        ).all()

        unique = len(groups)
        duplicates = total_q - unique if total_q > unique else 0
        dup_pct = (duplicates / total_q * 100) if total_q > 0 else 0

        most_frequent = sorted(groups, key=lambda g: g.frequency, reverse=True)[:10]

        return {
            "total_documents": sources,
            "total_questions": total_q,
            "unique_questions": unique,
            "duplicate_questions": duplicates,
            "duplicate_percentage": round(dup_pct, 1),
            "most_frequent_questions": [
                {
                    "id": g.id,
                    "question": g.canonical_question,
                    "frequency": g.frequency,
                    "topic": g.topic,
                }
                for g in most_frequent
            ],
        }

    def get_groups(
        self,
        collection_id: int,
        sort_by: str = "frequency",
        filter_year: Optional[str] = None,
        filter_frequency: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict]:
        """Get duplicate groups with filtering and sorting."""
        from models import DuplicateGroup, DuplicateGroupMember, ExtractedQuestion, Source

        query = self.db.query(DuplicateGroup).filter(
            DuplicateGroup.collection_id == collection_id
        )

        if filter_frequency:
            query = query.filter(DuplicateGroup.frequency >= filter_frequency)

        if search:
            query = query.filter(DuplicateGroup.canonical_question.ilike(f"%{search}%"))

        if sort_by == "frequency":
            query = query.order_by(DuplicateGroup.frequency.desc())
        elif sort_by == "alphabetical":
            query = query.order_by(DuplicateGroup.canonical_question)
        else:
            query = query.order_by(DuplicateGroup.frequency.desc())

        groups = query.all()
        result = []

        for group in groups:
            members = (
                self.db.query(DuplicateGroupMember)
                .filter(DuplicateGroupMember.group_id == group.id)
                .all()
            )

            member_data = []
            years = set()
            for m in members:
                question = self.db.query(ExtractedQuestion).filter(
                    ExtractedQuestion.id == m.question_id
                ).first()
                if not question:
                    continue

                source = self.db.query(Source).filter(
                    Source.id == question.source_id
                ).first()

                if question.year:
                    years.add(question.year)

                if filter_year and question.year != filter_year:
                    continue

                member_data.append({
                    "id": m.id,
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "similarity_score": m.similarity_score,
                    "source_filename": source.original_filename if source else "Unknown",
                    "year": question.year,
                    "page_number": question.page_number,
                    "question_type": question.question_type,
                })

            if filter_year and not member_data:
                continue

            result.append({
                "id": group.id,
                "canonical_question": group.canonical_question,
                "topic": group.topic,
                "frequency": group.frequency,
                "years": sorted(list(years)),
                "members": member_data,
            })

        return result

    def merge_groups(self, group_ids: List[int], user_id: int) -> Dict:
        """Merge multiple groups into one."""
        from models import DuplicateGroup, DuplicateGroupMember

        groups = (
            self.db.query(DuplicateGroup)
            .filter(DuplicateGroup.id.in_(group_ids))
            .all()
        )
        if len(groups) < 2:
            return {"error": "Need at least 2 groups to merge"}

        # Keep the first group as primary
        primary = groups[0]
        total_freq = primary.frequency

        for other_group in groups[1:]:
            # Move members to primary group
            members = (
                self.db.query(DuplicateGroupMember)
                .filter(DuplicateGroupMember.group_id == other_group.id)
                .all()
            )
            for m in members:
                m.group_id = primary.id
            total_freq += other_group.frequency
            self.db.delete(other_group)

        primary.frequency = total_freq
        self.db.commit()

        return {"message": "Groups merged", "primary_group_id": primary.id}

    def remove_question_from_group(self, group_id: int, question_id: int, user_id: int) -> Dict:
        """Remove a question from a group, creating a new single-item group."""
        from models import DuplicateGroup, DuplicateGroupMember, ExtractedQuestion

        member = (
            self.db.query(DuplicateGroupMember)
            .filter(
                DuplicateGroupMember.group_id == group_id,
                DuplicateGroupMember.question_id == question_id,
            )
            .first()
        )
        if not member:
            return {"error": "Member not found"}

        question = self.db.query(ExtractedQuestion).filter(
            ExtractedQuestion.id == question_id
        ).first()

        # Remove from current group
        self.db.delete(member)

        # Update frequency
        group = self.db.query(DuplicateGroup).filter(DuplicateGroup.id == group_id).first()
        if group:
            group.frequency = max(1, group.frequency - 1)

        # Create new single-item group
        new_group = DuplicateGroup(
            collection_id=question.collection_id,
            user_id=user_id,
            canonical_question=question.question_text,
            topic=self._infer_topic(question.question_text),
            frequency=1,
        )
        self.db.add(new_group)
        self.db.flush()

        new_member = DuplicateGroupMember(
            group_id=new_group.id,
            question_id=question_id,
            similarity_score=1.0,
        )
        self.db.add(new_member)
        self.db.commit()

        return {"message": "Question moved to new group", "new_group_id": new_group.id}

    def generate_consolidated_document(self, collection_id: int) -> Dict:
        """Generate a consolidated document with unique questions."""
        groups = self.get_groups(collection_id, sort_by="frequency")
        stats = self.get_stats(collection_id)

        # Organize by topic
        topics = defaultdict(list)
        for group in groups:
            topic = group.get("topic", "General")
            topics[topic].append(group)

        document = {
            "title": "Consolidated Question Bank - StudyMind AI",
            "stats": stats,
            "topics": [],
        }

        q_number = 1
        for topic_name, topic_groups in sorted(topics.items()):
            topic_data = {
                "name": topic_name,
                "questions": [],
            }
            for group in sorted(topic_groups, key=lambda g: g["frequency"], reverse=True):
                freq_label = "Very Important" if group["frequency"] >= 5 else \
                             "Important" if group["frequency"] >= 3 else \
                             "Moderate" if group["frequency"] >= 2 else "Normal"
                q_data = {
                    "number": q_number,
                    "question": group["canonical_question"],
                    "frequency": group["frequency"],
                    "frequency_label": freq_label,
                    "years": group.get("years", []),
                    "topic": topic_name,
                    "variations": [
                        {
                            "text": m["question_text"],
                            "source": m["source_filename"],
                            "year": m.get("year"),
                            "page": m.get("page_number"),
                        }
                        for m in group.get("members", [])
                    ],
                }
                topic_data["questions"].append(q_data)
                q_number += 1

            document["topics"].append(topic_data)

        return document
