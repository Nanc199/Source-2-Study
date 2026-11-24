"""
Source2Study - Duplicate Question Detector
Intelligent question extraction, cross-resource duplicate detection, and consolidation.
Specially tuned for Previous-Year Exam Papers (e.g., GATE, University, Competitive Exams).
"""

import os
import re
import json
import logging
from difflib import SequenceMatcher
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from config import settings

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Advanced AI-powered duplicate question detection and question bank consolidation system."""

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

    # ------------------------------------------------------------------
    # Extraction & Structuring
    # ------------------------------------------------------------------

    def extract_questions_from_source(self, source_id: int, user_id: int) -> List[Any]:
        """Extract individual questions from a source document (PDF, scanned PDF, image, docx)."""
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

        full_text = ""
        # 1. Prefer extracting directly from original PDF to avoid 200-char chunking overlap artifacts
        if source.file_path and os.path.isfile(source.file_path) and source.file_type == 'pdf':
            try:
                import fitz
                doc = fitz.open(source.file_path)
                pages_text = []
                for p_idx, page in enumerate(doc):
                    txt = page.get_text("text").strip()
                    if txt:
                        pages_text.append(f"[Page {p_idx + 1}]\n{txt}")
                doc.close()
                if pages_text:
                    full_text = "\n\n".join(pages_text)
            except Exception as e:
                logger.debug(f"Direct fitz extraction skipped: {e}")

        # 2. Fall back to extracted chunks if direct file extraction was not available
        if not full_text:
            if not chunks:
                return []
            full_text = "\n\n".join([c.content for c in chunks])

        year = self._extract_year(source.original_filename or source.filename or "")
        if not year:
            year = self._extract_year(full_text[:500])

        # Method 1: Structure-aware exam pattern extraction
        extracted_items = self._extract_by_patterns(full_text)

        # Method 2: Question mark-based segmentation if few found
        if len(extracted_items) < 2:
            qmark_questions = self._extract_by_question_marks(full_text)
            for item in qmark_questions:
                if not any(self._quick_similar(item["formatted_text"], eq["formatted_text"]) for eq in extracted_items):
                    extracted_items.append(item)

        # Method 3: AI-based extraction (if Gemini API key configured and very few questions extracted)
        if settings.GEMINI_API_KEY and len(extracted_items) < 3:
            try:
                ai_questions = self._extract_by_ai(full_text)
                for item in ai_questions:
                    if not any(self._quick_similar(item["formatted_text"], eq["formatted_text"]) for eq in extracted_items):
                        extracted_items.append(item)
            except Exception as e:
                logger.warning(f"AI question extraction fallback failed: {e}")

        # Store extracted questions with source and page attribution
        stored = []
        for item in extracted_items:
            formatted_text = item["formatted_text"].strip()
            normalized = item["normalized_text"].strip()
            q_type = item.get("question_type") or self._detect_question_type(formatted_text)

            if len(formatted_text) < 15 or len(formatted_text) > 4500:
                continue
            if len(normalized) < 8:
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

            page_num = self._find_page_number(formatted_text, chunks) or item.get("page_number")

            eq = ExtractedQuestion(
                source_id=source_id,
                collection_id=source.collection_id,
                user_id=user_id,
                question_text=formatted_text,
                normalized_text=normalized,
                question_type=q_type,
                page_number=page_num,
                year=year,
            )
            self.db.add(eq)
            stored.append(eq)

        self.db.commit()
        return stored

    def _is_administrative_or_instruction(self, text: str) -> bool:
        """Filter out non-question administrative boilerplate, exam instructions, and section titles."""
        t = text.lower().strip()

        # Instruction phrases found across university, college, and competitive exams
        instruction_phrases = [
            'carry one mark each', 'carry two marks each', 'carry 1 mark each', 'carry 2 marks each',
            'carrying one mark', 'carrying two marks', 'for each wrong answer', 'negative marks',
            'negative marking', 'there will be negative', 'scientific calculator is permitted',
            'charts, graph sheets or tables are not permitted', 'use of mobile phones',
            'candidates are not allowed', 'maximum marks', 'max marks', 'max. marks',
            'time allowed', 'duration: 3 hours', 'duration: 2 hours', 'duration:',
            'total questions:', 'end of the question paper', 'end of question paper',
            'draft answer key', 'final answer key', 'organizing institute', 'graduate aptitude test',
            'session 1', 'session 2', 'paper code:', 'answer key for',
            'answer all questions', 'answer any five', 'answer any four', 'answer any three',
            'all questions carry equal marks', 'each question carries equal marks',
            'write your roll number', 'write your register number', 'hall ticket number',
            'candidates must verify', 'rough work should be done', 'do not write anything on',
            'return the question paper', 'non-programmable calculator', 'calculator is permitted',
            'instructions to candidate', 'instructions to the candidate', 'general instructions',
            'read the instructions carefully', 'read the following instructions',
        ]
        for phrase in instruction_phrases:
            if phrase in t and len(t) < 400:
                return True

        # Pure section headings or university exam headers
        heading_patterns = [
            r'^(?:section|part|group|module|unit)\s*[-–—:]?\s*[a-z0-9\s:\-]+$',
            r'^(?:general aptitude|computer science|engineering mathematics|mechanical engineering|electrical engineering|civil engineering|information technology)\s*\(?[a-z\s]*\)?$',
            r'^[a-z]{2}\s*:\s*[a-z\s&]+$',
            r'^page\s+\d+\s+of\s+\d+$',
            r'^\[page\s+\d+\]$',
            r'^[a-z\s]+(?:university|college of engineering|institute of technology|department of [a-z\s]+)$',
            r'^(?:semester|annual|mid-?term)\s*examination\s*(?:19|20)?\d{2}$',
            r'^(?:b\.tech|b\.e\.|m\.tech|m\.ca|b\.sc|m\.sc)\s*(?:degree)?\s*(?:semester)?\s*exam[a-z\s0-9\-]*$',
        ]
        clean_oneline = re.sub(r'\s+', ' ', t).strip()
        for p in heading_patterns:
            if re.match(p, clean_oneline):
                return True

        return False

    def _clean_and_structure_question(self, raw_block: str, q_num: Optional[str] = None) -> Dict[str, Any]:
        """
        Cleans and structures a question block from an exam paper (GATE, university, college, competitive):
        - Strips page indicators and running footers
        - Strips general university, institute, department, and degree headings
        - Strips general examination instructions and candidate notices
        - Formats question statement clearly
        - Separates multiple-choice options (A, B, C, D) onto separate lines under **Options:**
        - Preserves mathematical formulas, equations, complexity notations (O(n log n), theta, etc.)
        - Distinguishes MCQ from NAT (numerical) and descriptive questions without inventing options
        """
        text = raw_block.strip()

        # 1. Strip page indicators
        page_match = re.search(r'\[Page\s+(\d+)\]', text, flags=re.IGNORECASE)
        found_page = int(page_match.group(1)) if page_match else None

        text = re.sub(r'\[Page\s+\d+\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:CS|EC|EE|ME|CE|IN|CH|BT|DA)\s+\d+/\d+\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\s*\d+\s*/\s*\d+\s*$', '', text, flags=re.MULTILINE)

        # 2. Strip general exam headers & footers across any exam paper
        text = re.sub(r'(?:Useful Data|USEFUL DATA)\s*:.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'END OF (?:THE )?(?:QUESTION )?PAPER.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'END OF PAPER.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'Draft Answer Key[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Final Answer Key[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?:All the best|Best of luck)[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Copyright\s*(?:©|\(c\))[^\n]*', '', text, flags=re.IGNORECASE)

        # General University & Institute titles
        text = re.sub(r'^[^\n]*(?:University|Institute of Technology|College of Engineering|Autonomous College|Board of Secondary)[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^[^\n]*(?:Degree Examination|Semester Examination|Mid-?term Examination|Annual Examination|Final Examination)[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^[^\n]*(?:Department of|Faculty of|School of)[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^[^\n]*(?:Branch|Discipline|Course Code|Subject Code|Paper Code)\s*:[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^[^\n]*(?:Time Allowed|Time|Duration)\s*:[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^[^\n]*(?:Maximum Marks|Max\.?\s*Marks|Total Marks)\s*:[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^[^\n]*(?:Roll No|Register No|Reg\.?\s*No|Hall Ticket No|Seat No)\s*:[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^[^\n]*(?:Organizing Institute|Graduate Aptitude Test in Engineering)[^\n]*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'GATE\s*(?:19|20)\d{2}[^\n]*', '', text, flags=re.IGNORECASE)

        # 3. Strip exam instruction boilerplate
        text = re.sub(r'Q\.\s*\d+\s*[-–—to]+\s*Q\.\s*\d+\s*[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?:Questions?\s*)?Q\.\s*\d+\s*[-–—to]+\s*Q\.\s*\d+[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?:carry|carrying)\s+(?:ONE|TWO|one|two|\d+)\s+marks?[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Negative\s+[Mm]arks?[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'For a wrong answer chosen[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[\s*\d+\s*(?:marks?|mark|m)\s*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\s*\d+\s*(?:marks?|mark|m)\s*\)', '', text, flags=re.IGNORECASE)

        # 4. Check for MCQ options: (A)... (B)... (C)... (D)... or A. B. C. D. or A) B) C) D)
        options_header_match = re.search(r'\n+\s*(?:\*\*)?Options\s*:(?:\*\*)?\s*\n*', text, flags=re.IGNORECASE)
        if options_header_match:
            statement_part = text[:options_header_match.start()].strip()
            options_part = text[options_header_match.end():].strip()
        else:
            opt_match = re.search(r'(?:(?:\n|\s{2,})(?:[A-Da-d][\.\)]|\([A-Da-d]\)|\[[A-Da-d]\])\s+)|(?:\([A-Da-d]\)\s+)', text)
            if opt_match:
                statement_part = text[:opt_match.start()].strip()
                options_part = text[opt_match.start():].strip()
            else:
                statement_part = text
                options_part = ""

        options_list = []
        parsed_opts = {}
        if options_part:
            raw_options = re.split(r'(?=(?:^|\n|\s{2,}|\t)(?:\([A-Da-d]\)|\[[A-Da-d]\]|[A-Da-d][\.\)]))\s*', options_part)
            for ro in raw_options:
                ro = ro.strip()
                if not ro:
                    continue
                m = re.match(r'^(?:\(([A-Da-d])\)|\[([A-Da-d])\]|([A-Da-d])[\.\)])\s*(.+)', ro, re.DOTALL)
                if m:
                    letter = (m.group(1) or m.group(2) or m.group(3)).upper()
                    opt_body = m.group(4).strip()
                    opt_body = re.sub(r'\[\s*\d+\s*(?:marks?|mark|m)\s*\]', '', opt_body, flags=re.IGNORECASE).strip()
                    parsed_opts[letter] = opt_body

        statement = statement_part if len(parsed_opts) >= 2 else text

        # Clean leading section titles or instructions from the statement
        statement = re.sub(
            r'^(?:(?:SECTION|PART|GROUP|MODULE|UNIT|PAPER)\s*[-–—:]?\s*[A-Z0-9\s]+(?:\([^\)]*\))?\s*[:\-–—]?\s*\n+)',
            '',
            statement,
            flags=re.IGNORECASE
        ).strip()
        statement = re.sub(
            r'^(?:(?:General\s+Instructions?|Instructions?\s*(?:to\s+Candidates?)?|Note)\s*[:\-–—]?\s*[^\n]*\n+)',
            '',
            statement,
            flags=re.IGNORECASE
        ).strip()

        # Remove redundant leading Q.num from statement
        if q_num:
            statement = re.sub(
                r'^(?:(?:Q\.?|Question|Problem)\s*)?' + re.escape(q_num) + r'\s*[\.:\)\-]?\s*',
                '',
                statement,
                flags=re.IGNORECASE
            ).strip()
        else:
            q_match = re.match(r'^(?:(?:Q\.?|Question|Problem)\s*)?(\d{1,3})\s*[\.:\)\-]\s*(.+)', statement, re.DOTALL | re.IGNORECASE)
            if q_match:
                q_num = q_match.group(1)
                statement = q_match.group(2).strip()

        # Clean any remaining leading punctuation like '.', ':', ')', '-'
        statement = re.sub(r'^\s*[\.:\)\-]\s*', '', statement).strip()

        # Ensure sub-statements (Statement I, Statement II, etc.) have proper line breaks
        statement = re.sub(r'([^\n])\n\s*(Statement\s+[I|V|X|\d]+:?)', r'\1\n\n\2', statement, flags=re.IGNORECASE)
        statement = re.sub(r'([^\n])\n\s*(\([i|v|x|\d]+\))', r'\1\n\n\2', statement, flags=re.IGNORECASE)
        statement = re.sub(r'\n{3,}', '\n\n', statement).strip()

        # Reconstruct clean, professionally formatted question
        q_label = f"**Question {q_num}**" if q_num else "**Question**"

        if len(parsed_opts) >= 2:
            formatted_options = []
            for l in ['A', 'B', 'C', 'D']:
                if l in parsed_opts:
                    formatted_options.append(f"{l}. {parsed_opts[l]}")
                    options_list.append(f"({l}) {parsed_opts[l]}")
            for l, val in parsed_opts.items():
                if l not in ['A', 'B', 'C', 'D']:
                    formatted_options.append(f"{l}. {val}")
                    options_list.append(f"({l}) {val}")

            options_block = "\n\n**Options:**\n\n" + "\n\n".join(formatted_options)
            formatted = f"{q_label}\n\n{statement}{options_block}"
            q_type = "mcq"
        else:
            formatted = f"{q_label}\n\n{statement}"
            stmt_lower = statement.lower()
            if "________" in statement or "_____" in statement or "numerical" in stmt_lower or "fill in the blank" in stmt_lower:
                q_type = "nat"
            else:
                q_type = self._detect_question_type(statement)

        normalized = self.normalize_question(formatted)

        return {
            "formatted_text": formatted,
            "normalized_text": normalized,
            "question_type": q_type,
            "q_num": q_num,
            "question_number": f"Question {q_num}" if q_num else None,
            "statement": statement,
            "options": options_list,
            "page_number": found_page,
        }

    def _extract_by_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Extract questions using numbering and exam boundary patterns across all academic exam types."""
        questions = []

        # Exam question boundary pattern: Question 1, Q.1, Q1., Problem 1, 1. (when followed by question content)
        boundary_pattern = re.compile(
            r'(?:^|\n)\s*(?:(?:Q(?:uestion)?\.?\s*)(\d{1,3})|(?:Problem\s*)(\d{1,3})|(\d{1,3}))\s*[\.:\)\-]?\s*',
            re.MULTILINE | re.IGNORECASE
        )

        matches = []
        for m in boundary_pattern.finditer(text):
            # Filter out range patterns like "Q.1 – Q.5 carry ONE mark" or "1 to 5"
            following_text = text[m.end():m.end() + 25]
            if re.match(r'^\s*[-–—to]+\s*(?:Q\.?\s*)?\d+', following_text, re.IGNORECASE):
                continue
            matches.append(m)

        if len(matches) >= 2:
            for idx in range(len(matches)):
                q_num = matches[idx].group(1) or matches[idx].group(2) or matches[idx].group(3)
                start = matches[idx].end()
                end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
                block = text[start:end].strip()

                # Clean trailing exam footers before administrative check
                block_clean = re.sub(r'(?:Useful Data|USEFUL DATA)\s*:.*$', '', block, flags=re.DOTALL | re.IGNORECASE).strip()
                block_clean = re.sub(r'END OF (?:THE )?(?:QUESTION )?PAPER.*$', '', block_clean, flags=re.DOTALL | re.IGNORECASE).strip()
                block_clean = re.sub(r'END OF PAPER.*$', '', block_clean, flags=re.DOTALL | re.IGNORECASE).strip()
                block_clean = re.sub(r'(?:All the best|Best of luck)[^\n]*', '', block_clean, flags=re.IGNORECASE).strip()

                if len(block_clean) > 15 and not self._is_administrative_or_instruction(block_clean) and self._is_likely_question(block_clean):
                    cleaned = self._clean_and_structure_question(block_clean, q_num)
                    if len(cleaned["statement"]) > 15 and not self._is_administrative_or_instruction(cleaned["statement"]):
                        questions.append(cleaned)

        # Fallback secondary regex if boundaries yielded too few
        if len(questions) < 2:
            secondary_pattern = re.compile(
                r'(?:^|\n)\s*(?:(?:Q(?:uestion)?\.?|Problem)\s*)(\d{1,3})\s*[\.:\)\-]\s*(.+?)(?=(?:\n\s*(?:Q(?:uestion)?\.?|Problem)\s*\d{1,3}\s*[\.:\)\-])|$)',
                re.DOTALL | re.IGNORECASE
            )
            for m in secondary_pattern.finditer(text):
                q_num = m.group(1)
                block = m.group(2).strip()
                block_clean = re.sub(r'(?:Useful Data|USEFUL DATA)\s*:.*$', '', block, flags=re.DOTALL | re.IGNORECASE).strip()
                block_clean = re.sub(r'END OF (?:THE )?(?:QUESTION )?PAPER.*$', '', block_clean, flags=re.DOTALL | re.IGNORECASE).strip()
                block_clean = re.sub(r'END OF PAPER.*$', '', block_clean, flags=re.DOTALL | re.IGNORECASE).strip()
                block_clean = re.sub(r'(?:All the best|Best of luck)[^\n]*', '', block_clean, flags=re.IGNORECASE).strip()

                if len(block_clean) > 15 and not self._is_administrative_or_instruction(block_clean) and self._is_likely_question(block_clean):
                    cleaned = self._clean_and_structure_question(block_clean, q_num)
                    if not any(self._quick_similar(cleaned["formatted_text"], q["formatted_text"]) for q in questions):
                        questions.append(cleaned)

        return questions

    def _is_likely_question(self, text: str) -> bool:
        """Verify that the block represents a substantive question rather than administrative text."""
        t_lower = text.lower().strip()
        if '?' in text and len(t_lower) > 15:
            return True

        # Check for multiple-choice options (A)... (B)... or A. ... B. ...
        if re.search(r'(?:\([A-Da-d]\)|\[[A-Da-d]\]|(?<=\s)[A-Da-d][\.\)])\s+', text):
            return True

        # Check for NAT blanks or numerical answer requirements
        if '________' in text or '_____' in text or 'numerical value' in t_lower:
            return True

        question_keywords = [
            'explain', 'define', 'describe', 'what is', 'what are', 'how do', 'why does',
            'discuss', 'compare', 'differentiate', 'distinguish', 'list', 'enumerate',
            'write a program', 'write an algorithm', 'derive', 'prove that', 'solve',
            'calculate', 'find the', 'show that', 'consider the', 'which of the following',
            'which one of the following', 'determine', 'evaluate', 'state the', 'formulate',
            'illustrate', 'let g be', 'let l be', 'let t be', 'suppose', 'given that', 'assume that',
            'the number of', 'the value of', 'match the following', 'minimum number of',
            'maximum number of', 'time complexity', 'space complexity', 'regular expression',
            'state and prove', 'simplify the', 'classify the', 'elaborate on', 'construct a',
            'design a', 'draw the', 'compute the',
        ]
        if any(kw in t_lower for kw in question_keywords):
            return True

        return False

    def _extract_by_question_marks(self, text: str) -> List[Dict[str, Any]]:
        """Extract sentences ending with question marks."""
        questions = []
        clean = re.sub(r'\[Page\s+\d+\]', '', text)
        sentences = re.split(r'(?<=\?)\s+', clean)

        for sent in sentences:
            sent = sent.strip()
            if '?' in sent:
                lines = sent.split('\n')
                q_candidate = " ".join([l.strip() for l in lines if l.strip()])
                if len(q_candidate) > 20 and self._is_likely_question(q_candidate) and not self._is_administrative_or_instruction(q_candidate):
                    cleaned = self._clean_and_structure_question(q_candidate)
                    questions.append(cleaned)

        return questions

    def _extract_by_ai(self, text: str) -> List[Dict[str, Any]]:
        """Use Gemini to extract questions from unstructured text with structured formatting."""
        from services.rag_service import RAGService
        rag = RAGService()

        prompt = f"""Extract ALL academic exam and test questions from the following text.
Return each question formatted clearly. If it is an MCQ, preserve options (A), (B), (C), (D) on separate lines.
Do NOT include answers, page headers, instructions, or administrative text.

TEXT:
{text[:9000]}

Format each question as:
Q.<number>: <Question Statement>
(A) <Option A>
(B) <Option B>
(C) <Option C>
(D) <Option D>

Separate questions with '---':"""

        try:
            response = rag._call_gemini(prompt, max_output_tokens=2200, timeout_ms=12000)
            blocks = response.split('---')
            questions = []
            for b in blocks:
                b = b.strip()
                if len(b) > 20 and self._is_likely_question(b) and not self._is_administrative_or_instruction(b):
                    cleaned = self._clean_and_structure_question(b)
                    questions.append(cleaned)
            return questions
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Normalization & Domain Opposing Entity Filtering
    # ------------------------------------------------------------------

    def normalize_question(self, text: str) -> str:
        """Normalize question text for comparison while preserving core semantics and math terms."""
        text = text.lower().strip()
        # Remove markdown headers like **Question 1**, Question 1:, Q.1:
        text = re.sub(r'^\s*\*\*(?:question|q\.?|problem)\s*\d*\*\*\s*', '', text)
        text = re.sub(r'^(?:(?:question|q|problem)\s*\.?\s*)?(?:\d{1,3})\s*[\.\)\]:\s\-]+', '', text)
        text = re.sub(r'^\([a-za-z0-9]\)\s*', '', text)
        # Remove **Options:** or Options: header
        text = re.sub(r'\*\*(?:options|option)\s*:\*\*', ' ', text)
        text = re.sub(r'\boptions\s*:', ' ', text)
        # Remove option letter prefixes: a. b. c. d. or (a) (b) (c) (d)
        text = re.sub(r'\b[a-d]\s*[\.\)]\s*', ' ', text)
        text = re.sub(r'\([a-d]\)\s*', ' ', text)
        # Remove marks indicators like [5 Marks], (10M)
        text = re.sub(r'\[\s*\d+\s*(?:marks?|m)\s*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\s*\d+\s*(?:marks?|mark|m)\s*\)', '', text, flags=re.IGNORECASE)
        # Normalize punctuation while keeping hyphens and alphanumeric characters
        text = re.sub(r'[^\w\s\?\-\^]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _quick_similar(self, q1: str, q2: str) -> bool:
        """Fast preliminary similarity check for exact/near-exact duplicates."""
        n1 = self.normalize_question(q1)
        n2 = self.normalize_question(q2)
        if n1 == n2:
            return True

        w1 = set(n1.split())
        w2 = set(n2.split())
        if not w1 or not w2:
            return False

        overlap = len(w1 & w2) / max(len(w1), len(w2))
        return overlap > 0.90

    def _has_conflicting_domain_entities(self, q1: str, q2: str) -> bool:
        """
        Check for conflicting domain entities to avoid merging distinct questions on same subject.
        Prevents false positives on opposing concepts (e.g. worst-case vs best-case, preemptive vs non-preemptive).
        """
        opposing_pairs = [
            ({'worst', 'worst-case'}, {'best', 'best-case'}),
            ({'average', 'average-case'}, {'worst', 'worst-case'}),
            ({'average', 'average-case'}, {'best', 'best-case'}),
            ({'preemptive'}, {'non-preemptive', 'nonpreemptive'}),
            ({'starvation'}, {'deadlock'}),
            ({'bfs', 'breadth'}, {'dfs', 'depth'}),
            ({'tcp'}, {'udp'}),
            ({'minimum', 'min'}, {'maximum', 'max'}),
            ({'singly'}, {'doubly'}),
            ({'stack'}, {'queue'}),
            ({'compiler'}, {'interpreter'}),
            ({'synchronous', 'sync'}, {'asynchronous', 'async'}),
            ({'process'}, {'thread'}),
            ({'supervised'}, {'unsupervised'}),
            ({'symmetric'}, {'asymmetric'}),
            ({'primary'}, {'foreign'}),
            ({'bubble'}, {'quick'}),
            ({'merge'}, {'heap'}),
            ({'quick'}, {'merge'}),
            ({'directed'}, {'undirected'}),
            ({'static'}, {'dynamic'}),
            ({'lossless'}, {'lossy'}),
            ({'inorder'}, {'preorder'}),
            ({'inorder'}, {'postorder'}),
            ({'preorder'}, {'postorder'}),
            ({'little-endian', 'little endian'}, {'big-endian', 'big endian'}),
            ({'ascending', 'increasing'}, {'descending', 'decreasing'}),
            ({'internal'}, {'external'}),
            ({'dense'}, {'sparse'}),
            ({'prims', 'prim'}, {'kruskal', 'kruskals'}),
            ({'dijkstra', 'dijkstras'}, {'bellman-ford', 'bellman'}),
            ({'paging'}, {'segmentation'}),
            ({'np-complete', 'np complete'}, {'p', 'polynomial'}),
            ({'sram'}, {'dram'}),
            ({'risc'}, {'cisc'}),
            ({'left'}, {'right'}),
        ]

        words1 = set(re.findall(r'\b[a-z\-]+\b', q1.lower()))
        words2 = set(re.findall(r'\b[a-z\-]+\b', q2.lower()))

        for set_a, set_b in opposing_pairs:
            in_q1_a = bool(words1 & set_a)
            in_q1_b = bool(words1 & set_b)
            in_q2_a = bool(words2 & set_a)
            in_q2_b = bool(words2 & set_b)

            if (in_q1_a and not in_q1_b and in_q2_b and not in_q2_a) or \
               (in_q1_b and not in_q1_a and in_q2_a and not in_q2_b):
                return True

        return False

    def _classify_match_type(self, sim: float, q1_norm: str, q2_norm: str) -> str:
        """Classify degree of duplicate similarity."""
        if q1_norm == q2_norm or sim >= 0.98:
            return "Exact Duplicate"
        if sim >= 0.88:
            return "Near Duplicate"
        return "Conceptual Duplicate"

    # ------------------------------------------------------------------
    # Main Detection Pipeline
    # ------------------------------------------------------------------

    def detect_duplicates(
        self,
        collection_id: int,
        user_id: int,
        similarity_threshold: Optional[float] = None,
        use_llm_verification: bool = True,
        source_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Main duplicate detection and grouping pipeline across uploaded resources."""
        from models import ExtractedQuestion, DuplicateGroup, DuplicateGroupMember, Source

        if similarity_threshold is None:
            # High precision default threshold (0.88) to prevent false positives
            similarity_threshold = 0.88

        # Step 1: Identify target sources
        source_query = self.db.query(Source).filter(
            Source.status == "completed"
        )
        if source_ids:
            source_query = source_query.filter(Source.id.in_(source_ids), Source.user_id == user_id)
        else:
            source_query = source_query.filter(Source.collection_id == collection_id, Source.user_id == user_id)

        sources = source_query.all()
        target_source_ids = [s.id for s in sources]

        # Extract questions for sources that don't have them yet
        for source in sources:
            existing_count = (
                self.db.query(ExtractedQuestion)
                .filter(ExtractedQuestion.source_id == source.id)
                .count()
            )
            if existing_count == 0:
                self.extract_questions_from_source(source.id, user_id)

        # Step 2: Query all relevant questions
        if target_source_ids:
            q_query = self.db.query(ExtractedQuestion).filter(
                ExtractedQuestion.source_id.in_(target_source_ids)
            )
        else:
            q_query = self.db.query(ExtractedQuestion).filter(
                ExtractedQuestion.collection_id == collection_id
            )

        questions = q_query.order_by(ExtractedQuestion.created_at).all()
        total_pages = sum((s.page_count or 1) for s in sources)

        if len(questions) < 2:
            unique_list = []
            for q in questions:
                src = next((s for s in sources if s.id == q.source_id), None)
                src_name = src.original_filename if src else "Resource"
                q_num = self._extract_q_number(q.question_text)
                unique_list.append({
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_number": q_num,
                    "source_filename": src_name,
                    "page_number": q.page_number,
                    "year": q.year,
                    "frequency": 1,
                    "topic": self._infer_topic(q.question_text),
                    "question_type": q.question_type or self._detect_question_type(q.question_text),
                    "all_sources": [{
                        "source_filename": src_name,
                        "year": q.year,
                        "page_number": q.page_number,
                        "question_number": q_num,
                    }],
                })
            return {
                "total_documents": len(sources),
                "total_pages_processed": total_pages,
                "total_questions": len(questions),
                "unique_questions": len(questions),
                "repeated_groups_count": 0,
                "total_duplicate_occurrences": 0,
                "duplicate_percentage": 0.0,
                "repeated_question_groups": [],
                "unique_questions_list": unique_list,
            }

        # Step 3: Compute embeddings with SentenceTransformers
        texts = [q.normalized_text for q in questions]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings)

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings_normalized = embeddings / norms

        # Step 4: Calculate cosine similarity matrix
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)

        # Step 5: Union-Find grouping
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

        ambiguous_pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                q1_norm = questions[i].normalized_text
                q2_norm = questions[j].normalized_text
                sim = float(similarity_matrix[i][j])

                # Check opposing domain entities FIRST (prevent false positives)
                if self._has_conflicting_domain_entities(q1_norm, q2_norm):
                    continue

                # Exact duplicate match
                if q1_norm == q2_norm:
                    union(i, j)
                    continue

                # Near duplicate via high token / fuzzy ratio
                sm_ratio = SequenceMatcher(None, q1_norm, q2_norm, autojunk=False).ratio()
                if sm_ratio >= 0.90:
                    union(i, j)
                    continue

                # Semantic duplicate via embeddings (strictly at or above threshold)
                if sim >= similarity_threshold:
                    union(i, j)
                elif sim >= (similarity_threshold - 0.05) and use_llm_verification:
                    ambiguous_pairs.append((i, j, sim))

        # Step 6: LLM verification for ambiguous pairs (up to 10 pairs with 4s timeout)
        if ambiguous_pairs and settings.GEMINI_API_KEY:
            for i, j, sim in ambiguous_pairs[:10]:
                try:
                    if self._llm_verify_duplicate(questions[i].question_text, questions[j].question_text):
                        union(i, j)
                except Exception as e:
                    logger.warning(f"LLM verification failed: {e}")

        # Step 7: Group members
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)

        # Step 8: Clear existing groups for this collection/target sources
        old_groups = (
            self.db.query(DuplicateGroup)
            .filter(DuplicateGroup.collection_id == collection_id)
            .all()
        )
        for g in old_groups:
            self.db.delete(g)
        self.db.flush()

        # Step 9: Create DuplicateGroup & DuplicateGroupMember rows
        repeated_groups_data = []
        strictly_unique_list = []
        total_duplicate_occurrences = 0

        source_map = {s.id: s for s in sources}

        for rep_idx, member_indices in groups.items():
            member_questions = [questions[i] for i in member_indices]
            # Canonical question: most comprehensive question phrasing (with options preferred)
            canonical = max(member_questions, key=lambda q: (1 if "(A)" in q.question_text else 0, len(q.question_text)))
            canonical_q_num = self._extract_q_number(canonical.question_text)
            topic = self._infer_topic(canonical.question_text)
            freq = len(member_indices)

            group = DuplicateGroup(
                collection_id=collection_id,
                user_id=user_id,
                canonical_question=canonical.question_text,
                topic=topic,
                frequency=freq,
            )
            self.db.add(group)
            self.db.flush()

            member_details = []
            all_sources_info = []
            years = set()

            for idx in member_indices:
                q = questions[idx]
                sim = float(similarity_matrix[rep_idx][idx]) if idx != rep_idx else 1.0
                member = DuplicateGroupMember(
                    group_id=group.id,
                    question_id=q.id,
                    similarity_score=sim,
                )
                self.db.add(member)

                src = source_map.get(q.source_id)
                src_filename = src.original_filename if src else "Resource"
                if q.year:
                    years.add(q.year)

                m_q_num = self._extract_q_number(q.question_text)
                match_type = self._classify_match_type(sim, canonical.normalized_text, q.normalized_text)

                m_info = {
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "question_number": m_q_num,
                    "similarity_score": round(sim, 3),
                    "match_type": match_type,
                    "source_filename": src_filename,
                    "page_number": q.page_number,
                    "year": q.year,
                    "question_type": q.question_type or self._detect_question_type(q.question_text),
                }
                member_details.append(m_info)
                all_sources_info.append({
                    "source_filename": src_filename,
                    "year": q.year,
                    "page_number": q.page_number,
                    "question_number": m_q_num,
                })

            primary_src = source_map.get(canonical.source_id)

            # STRICT MUTUAL EXCLUSIVITY:
            # - If freq == 1: it appears in ONLY ONE paper -> strictly unique
            # - If freq > 1: it appeared in MULTIPLE papers -> strictly repeated
            if freq == 1:
                strictly_unique_list.append({
                    "id": canonical.id,
                    "question_text": canonical.question_text,
                    "question_number": canonical_q_num,
                    "source_filename": primary_src.original_filename if primary_src else "Resource",
                    "page_number": canonical.page_number,
                    "year": canonical.year,
                    "years": sorted(list(years)),
                    "frequency": 1,
                    "topic": topic,
                    "question_type": canonical.question_type or self._detect_question_type(canonical.question_text),
                    "all_sources": all_sources_info,
                })
            else:
                total_duplicate_occurrences += (freq - 1)
                repeated_groups_data.append({
                    "id": group.id,
                    "canonical_question": canonical.question_text,
                    "question_number": canonical_q_num,
                    "frequency": freq,
                    "topic": topic,
                    "years": sorted(list(years)),
                    "members": member_details,
                })

        self.db.commit()

        # Sort repeated groups by frequency descending
        repeated_groups_data.sort(key=lambda g: g["frequency"], reverse=True)

        total_q = len(questions)
        distinct_concepts = len(groups)
        dup_pct = (total_duplicate_occurrences / total_q * 100) if total_q > 0 else 0

        return {
            "total_documents": len(sources),
            "total_pages_processed": total_pages,
            "total_questions": total_q,
            "unique_questions": len(strictly_unique_list),
            "distinct_question_concepts": distinct_concepts,
            "repeated_groups_count": len(repeated_groups_data),
            "total_duplicate_occurrences": total_duplicate_occurrences,
            "duplicate_percentage": round(dup_pct, 1),
            "repeated_question_groups": repeated_groups_data,
            "unique_questions_list": strictly_unique_list,
        }

    def _llm_verify_duplicate(self, q1: str, q2: str) -> bool:
        """Use Gemini to confirm whether two questions ask essentially the same question."""
        from services.rag_service import RAGService
        rag = RAGService()

        prompt = f"""Determine if these two exam questions are asking essentially the SAME question (just worded differently) or if they are asking DIFFERENT questions.
IMPORTANT RULES:
- "Define Machine Learning" and "What do you mean by Machine Learning?" -> SAME
- "Explain BFS" and "Explain DFS" -> DIFFERENT (different algorithms)
- "What is TCP?" and "What is UDP?" -> DIFFERENT
- "Find the maximum subarray sum" and "Find the minimum subarray sum" -> DIFFERENT
- "Worst-case time complexity of Quick Sort" and "Best-case time complexity of Quick Sort" -> DIFFERENT
- Two different questions merely on the same subject (e.g. two different questions about CPU scheduling) -> DIFFERENT

Question 1: {q1[:500]}
Question 2: {q2[:500]}

Answer ONLY with "SAME" or "DIFFERENT":"""

        try:
            response = rag._call_gemini(prompt, max_output_tokens=20, timeout_ms=5000).strip().upper()
            return "SAME" in response
        except Exception:
            return False

    def _extract_q_number(self, text: str) -> str:
        """Extract question number like Q.1, Q.23, or 15."""
        m = re.match(r'^(?:(?:Q(?:uestion)?\.?\s*)(\d{1,3})|(\d{1,3}))[\.:\)\-\s]', text.strip(), re.IGNORECASE)
        if m:
            num = m.group(1) or m.group(2)
            return f"Q.{num}"
        return "Q"

    def _detect_question_type(self, text: str) -> str:
        """Categorize question as MCQ, NAT, short, long, or medium."""
        text_lower = text.lower()
        if re.search(r'\([A-Da-d]\)\s+', text):
            return "mcq"

        if "________" in text or "numerical" in text_lower or "fill in the blank" in text_lower:
            return "nat"

        marks_match = re.search(r'(\d+)\s*marks?', text_lower)
        if marks_match:
            marks = int(marks_match.group(1))
            return "short" if marks <= 5 else "long"

        short_keywords = ['define', 'state', 'list', 'name', 'what is', 'what are', 'write short note']
        long_keywords = ['explain in detail', 'discuss', 'elaborate', 'describe in detail', 'compare and contrast', 'derive']

        for kw in long_keywords:
            if kw in text_lower:
                return "long"
        for kw in short_keywords:
            if kw in text_lower:
                return "short"

        return "medium"

    def _find_page_number(self, question: str, chunks) -> Optional[int]:
        """Locate the page number where a question appears."""
        q_snippet = question[:70].strip()
        for chunk in chunks:
            if q_snippet and q_snippet in chunk.content:
                return chunk.page_number

        q_words = set(re.findall(r'\w{4,}', question.lower()))
        if not q_words:
            return None

        best_page = None
        best_overlap = 0

        for chunk in chunks:
            c_words = set(re.findall(r'\w{4,}', chunk.content.lower()))
            overlap = len(q_words & c_words)
            if overlap > best_overlap and overlap >= 3:
                best_overlap = overlap
                best_page = chunk.page_number

        return best_page

    def _extract_year(self, text: str) -> Optional[str]:
        """Extract 4-digit exam year (e.g. 2021, 2022, 2023, 2024)."""
        match = re.search(r'(?:20|19)\d{2}', text)
        return match.group(0) if match else None

    def _infer_topic(self, question: str) -> str:
        """Infer academic subject topic from question content."""
        question_lower = question.lower()
        topic_keywords = {
            "Artificial Intelligence": ["artificial intelligence", " ai ", "ai?", "heuristic", "minimax", "alpha-beta"],
            "Machine Learning": ["machine learning", " ml ", "regression", "classification", "clustering", "gradient descent"],
            "Deep Learning": ["deep learning", "neural network", "cnn", "rnn", "transformer", "backpropagation"],
            "Data Structures": ["data structure", "linked list", "tree", "graph", "stack", "queue", "binary search tree", "avl", "b-tree", "heap"],
            "Algorithms": ["algorithm", "sorting", "searching", "complexity", "time complexity", "dynamic programming", "greedy", "divide and conquer"],
            "Database Systems": ["database", "sql", "normalization", "dbms", "relational", "b+ tree", "transaction", "acid", "serializability"],
            "Operating Systems": ["operating system", " os ", "process", "thread", "scheduling", "deadlock", "semaphore", "virtual memory", "paging"],
            "Computer Networks": ["network", "tcp", "ip", "protocol", "osi", "routing", "subnet", "congestion", "dns", "http"],
            "Theory of Computation": ["turing machine", "automata", "grammar", "cfg", "regular expression", "np-complete", "decidability", "pumping lemma"],
            "Computer Organization": ["cache", "pipelining", "processor", "instruction", "registers", "addressing modes", "alu", "memory hierarchy"],
            "Software Engineering": ["software engineering", "sdlc", "agile", "testing", "design pattern", "cohesion", "coupling"],
            "Discrete Mathematics": ["propositional logic", "combinatorics", "set theory", "relation", "recurrence relation", "graph theory", "probability"],
        }

        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in question_lower:
                    return topic

        words = re.sub(r'[^\w\s]', '', question).split()
        significant = [
            w for w in words
            if len(w) > 3 and w.lower() not in {
                'what', 'explain', 'define', 'describe', 'discuss', 'with', 'from', 'that', 'this', 'have', 'been', 'which'
            }
        ]
        return " ".join(significant[:2]).title() if significant else "General Concepts"

    def get_stats(self, collection_id: int) -> Dict:
        """Get duplicate detection summary statistics."""
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

        repeated_groups = [g for g in groups if g.frequency > 1]
        unique = len([g for g in groups if g.frequency == 1])
        duplicates = sum(g.frequency - 1 for g in repeated_groups)
        dup_pct = (duplicates / total_q * 100) if total_q > 0 else 0

        return {
            "total_documents": sources,
            "total_questions": total_q,
            "unique_questions": unique,
            "repeated_groups_count": len(repeated_groups),
            "duplicate_questions": duplicates,
            "duplicate_percentage": round(dup_pct, 1),
        }

    def get_groups(
        self,
        collection_id: int,
        sort_by: str = "frequency",
        filter_year: Optional[str] = None,
        filter_frequency: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict]:
        """Get duplicate question groups with optional filters."""
        from models import DuplicateGroup, DuplicateGroupMember, ExtractedQuestion, Source

        query = self.db.query(DuplicateGroup).filter(
            DuplicateGroup.collection_id == collection_id
        )

        if filter_frequency:
            query = query.filter(DuplicateGroup.frequency >= filter_frequency)

        if search:
            query = query.filter(DuplicateGroup.canonical_question.ilike(f"%{search}%"))

        if sort_by == "alphabetical":
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

                m_q_num = self._extract_q_number(question.question_text)
                sim = m.similarity_score
                match_type = self._classify_match_type(sim, group.canonical_question, question.question_text)

                member_data.append({
                    "id": m.id,
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "question_number": m_q_num,
                    "similarity_score": round(sim, 3),
                    "match_type": match_type,
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
                "question_number": self._extract_q_number(group.canonical_question),
                "topic": group.topic,
                "frequency": group.frequency,
                "years": sorted(list(years)),
                "members": member_data,
            })

        return result
