"""
app/services/parser_service.py
──────────────────────────────
PURPOSE:
  Document Ingestion & Parsing Engine for Phase 4.
  Extracts text from .md, .txt, and .pdf documents,
  then heuristically extracts structured Requirements, User Stories, and Acceptance Criteria.
"""
import io
import logging
import re
from typing import Any, Dict, List, Tuple
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DocumentParserService:
    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """
        Extracts raw string content and identifies file type (.md, .txt, .pdf).
        Returns: (extracted_text, file_type)
        """
        lower_name = filename.lower()
        if lower_name.endswith(".pdf"):
            file_type = "pdf"
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                text_parts = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                extracted = "\n\n".join(text_parts).strip()
                if not extracted:
                    raise ValueError("The PDF document does not contain readable text or is empty.")
                return extracted, file_type
            except Exception as e:
                logger.error(f"Error reading PDF '{filename}': {str(e)}")
                raise ValueError(f"Failed to extract text from PDF: {str(e)}")

        elif lower_name.endswith(".md"):
            file_type = "markdown"
            try:
                return file_bytes.decode("utf-8").strip(), file_type
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1").strip(), file_type

        elif lower_name.endswith(".txt"):
            file_type = "text"
            try:
                return file_bytes.decode("utf-8").strip(), file_type
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1").strip(), file_type

        else:
            raise ValueError("Unsupported file format. Please upload .md, .txt, or .pdf files.")

    @staticmethod
    def parse_requirements(raw_text: str) -> List[Dict[str, Any]]:
        """
        Heuristically parses raw document text into structured requirements.
        Handles:
        1. Markdown sections with headings (#, ##, ###)
        2. User story patterns ('As a ... I want ... So that ...')
        3. Acceptance criteria ('Given... When... Then...' or list items)
        4. Plain text section fallback
        """
        if not raw_text.strip():
            return []

        # Try markdown header splitting first
        sections = DocumentParserService._split_by_markdown_headers(raw_text)

        if not sections or len(sections) == 1 and not DocumentParserService._has_explicit_headers(raw_text):
            # Fallback to paragraph / numbered list splitting
            sections = DocumentParserService._split_by_paragraphs_or_numbers(raw_text)

        parsed_items: List[Dict[str, Any]] = []

        for title, body in sections:
            clean_title = title.strip()
            if not clean_title or clean_title.lower() in ("table of contents", "overview", "introduction", "document control"):
                continue

            category = DocumentParserService._infer_category(clean_title + " " + body)
            priority = DocumentParserService._infer_priority(clean_title + " " + body)
            description, criteria = DocumentParserService._extract_description_and_criteria(body)

            if not description and not criteria:
                description = clean_title

            # Ensure at least one default acceptance criterion if none parsed
            if not criteria:
                criteria = [f"Verify that {clean_title} behaves according to specification."]

            parsed_items.append({
                "title": clean_title[:255],
                "description": description.strip() if description else None,
                "category": category,
                "priority": priority,
                "status": "draft",
                "acceptance_criteria": criteria,
            })

        return parsed_items

    @staticmethod
    def _has_explicit_headers(text: str) -> bool:
        return bool(re.search(r'(?m)^#{1,4}\s+[^\n]+', text))

    @staticmethod
    def _split_by_markdown_headers(text: str) -> List[Tuple[str, str]]:
        """
        Splits text into (Heading, Content) pairs by Markdown headers.
        """
        header_pattern = re.compile(r'(?m)^(#{1,4})\s+(.+)$')
        matches = list(header_pattern.finditer(text))

        if not matches:
            return []

        sections: List[Tuple[str, str]] = []
        for i, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            sections.append((title, body))

        return sections

    @staticmethod
    def _split_by_paragraphs_or_numbers(text: str) -> List[Tuple[str, str]]:
        """
        Splits plain text by numbered items (e.g., '1.', 'REQ-1:', 'Feature:') or paragraphs.
        """
        pattern = re.compile(r'(?m)^(?:\d+\.|\bREQ-\d+:?|\bFeature:?|\bRequirement:?)\s*(.+)$')
        matches = list(pattern.finditer(text))

        if matches:
            sections: List[Tuple[str, str]] = []
            for i, match in enumerate(matches):
                title = match.group(1).strip()
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                body = text[start:end].strip()
                sections.append((title, body))
            return sections

        # Otherwise split by double newlines into chunks
        chunks = [c.strip() for c in re.split(r'\n{2,}', text) if c.strip()]
        sections = []
        for chunk in chunks:
            lines = chunk.split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else title
            sections.append((title[:80], body))
        return sections

    @staticmethod
    def _extract_description_and_criteria(body: str) -> Tuple[str, List[str]]:
        """
        Extracts narrative description and explicit acceptance criteria.
        """
        criteria: List[str] = []
        desc_lines: List[str] = []

        lines = body.split("\n")
        in_criteria_section = False

        criteria_header_pattern = re.compile(r'(?i)^(?:acceptance criteria|criteria|test conditions|expected behavior):?')
        user_story_pattern = re.compile(r'(?i)(as an?\s+[^\n,]+[,\s]+i want\s+[^\n,]+(?:[,\s]+so that\s+[^\n]+)?)')
        given_when_then_pattern = re.compile(r'(?i)(given\s+[^\n]+\s+when\s+[^\n]+\s+then\s+[^\n]+)')
        bullet_pattern = re.compile(r'^\s*[-*•]\s*(?:\[[ xX]\]\s*)?(.+)$')
        numbered_pattern = re.compile(r'^\s*\d+[\.\)]\s*(.+)$')

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if criteria_header_pattern.match(stripped):
                in_criteria_section = True
                continue

            # Check for Given/When/Then inline criteria
            gwt_match = given_when_then_pattern.search(stripped)
            if gwt_match:
                criteria.append(gwt_match.group(1).strip())
                continue

            if in_criteria_section:
                bullet = bullet_pattern.match(line)
                num = numbered_pattern.match(line)
                if bullet:
                    criteria.append(bullet.group(1).strip())
                elif num:
                    criteria.append(num.group(1).strip())
                else:
                    criteria.append(stripped)
            else:
                bullet = bullet_pattern.match(line)
                num = numbered_pattern.match(line)
                # If it looks like a checklist under a story, treat as criteria
                if bullet:
                    criteria.append(bullet.group(1).strip())
                elif num:
                    criteria.append(num.group(1).strip())
                else:
                    desc_lines.append(stripped)

        return "\n".join(desc_lines), criteria

    @staticmethod
    def _infer_category(text: str) -> str:
        t = text.lower()
        if any(w in t for w in ("security", "auth", "login", "password", "token", "permission", "rbac", "encrypt")):
            return "security"
        if any(w in t for w in ("ui", "ux", "design", "layout", "button", "screen", "modal", "view", "theme")):
            return "ui_ux"
        if any(w in t for w in ("performance", "latency", "throughput", "scale", "speed", "load time", "concurrent")):
            return "performance"
        if any(w in t for w in ("compliance", "audit", "reliability", "sla", "availability")):
            return "non_functional"
        return "functional"

    @staticmethod
    def _infer_priority(text: str) -> str:
        t = text.lower()
        if any(w in t for w in ("critical", "blocker", "emergency", "must-have", "mandatory", "p0")):
            return "critical"
        if any(w in t for w in ("high", "urgent", "important", "p1")):
            return "high"
        if any(w in t for w in ("low", "nice-to-have", "minor", "trivial", "optional", "p3")):
            return "low"
        return "medium"
