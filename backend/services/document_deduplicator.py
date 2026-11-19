"""Fast, local removal of repeated passages across completed study documents."""

import re
from difflib import SequenceMatcher
from typing import Dict, List


class DocumentDeduplicator:
    """Create a readable text document with repeated passages kept only once."""

    _PAGE_MARKER = re.compile(r"\[Page\s+\d+\]", re.IGNORECASE)
    _LEADING_NUMBER = re.compile(r"^(?:(?:question|q)\s*)?\d{1,3}\s*[.):\]-]\s*", re.IGNORECASE)

    def deduplicate(self, sources, chunks_by_source: Dict[int, list]) -> Dict:
        passages = []
        for source in sources:
            source_chunks = chunks_by_source.get(source.id, [])
            text = "\n".join(chunk.content for chunk in source_chunks)
            text = self._PAGE_MARKER.sub("\n", text)
            passages.extend(self._split_passages(text))

        kept = []
        normalized_kept = []
        token_index: Dict[str, set] = {}
        removed = 0

        for passage in passages:
            normalized, tokens = self._normalize(passage)
            if not normalized:
                continue

            # Candidate lookup avoids comparing every sentence with every other one.
            candidate_ids = set()
            for token in tokens:
                if len(token) >= 4:
                    candidate_ids.update(token_index.get(token, ()))

            duplicate = False
            token_set = set(tokens)
            for idx in candidate_ids:
                existing = normalized_kept[idx]
                if normalized == existing:
                    duplicate = True
                    break
                existing_tokens = set(existing.split())
                shorter = min(len(normalized), len(existing))
                longer = max(len(normalized), len(existing))
                if shorter >= 28 and shorter / max(longer, 1) >= 0.82:
                    if SequenceMatcher(None, normalized, existing, autojunk=False).ratio() >= 0.94:
                        duplicate = True
                        break
                if len(token_set) >= 8 and len(existing_tokens) >= 8:
                    overlap = len(token_set & existing_tokens) / len(token_set | existing_tokens)
                    if overlap >= 0.92:
                        duplicate = True
                        break

            if duplicate:
                removed += 1
                continue

            idx = len(kept)
            kept.append(passage)
            normalized_kept.append(normalized)
            for token in token_set:
                if len(token) >= 4:
                    token_index.setdefault(token, set()).add(idx)

        content = "\n\n".join(kept).strip()
        return {
            "title": "Duplicate-Free Study Material",
            "source_count": len(sources),
            "passage_count": len(passages),
            "unique_passage_count": len(kept),
            "duplicates_removed": removed,
            "content": content,
        }

    def _split_passages(self, text: str) -> List[str]:
        # A question mark/period or source line break is a useful unit for comparing
        # question papers, even when PDF extraction wraps content differently.
        parts = re.split(r"(?<=[.!?])\s+|\r?\n+", text)
        result = []
        for part in parts:
            part = re.sub(r"^\s*(?:[-*•]|\(?[a-z]\)|\d+[.)])\s*", "", part, flags=re.IGNORECASE)
            part = re.sub(r"\s+", " ", part).strip()
            if part:
                result.append(part)
        return result

    def _normalize(self, text: str):
        normalized = self._LEADING_NUMBER.sub("", text.strip().lower())
        tokens = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        return " ".join(tokens), tokens
