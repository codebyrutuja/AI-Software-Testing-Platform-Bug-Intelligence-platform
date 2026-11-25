"""
app/repositories/requirement_repository.py
──────────────────────────────────────────
PURPOSE: All database queries for Requirements, AcceptanceCriteria, and RequirementDocuments.
"""
import logging
import re
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.requirement import (
    AcceptanceCriteria,
    DocParsingStatus,
    Requirement,
    RequirementCategory,
    RequirementDocument,
    RequirementPriority,
    RequirementStatus,
)

logger = logging.getLogger(__name__)


class RequirementRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Key Generation Helper ───────────────────────────────────────────────────

    def get_next_req_key(self, project_id: str | UUID, project_key: str) -> str:
        """
        Calculates the next sequential requirement key for a project.
        Format: {PROJECT_KEY}-REQ-{NUMBER}, e.g. AUTH-REQ-01
        """
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        prefix = f"{project_key.upper()}-REQ-"

        # Query all keys for this project starting with the prefix
        keys = (
            self.db.query(Requirement.req_key)
            .filter(Requirement.project_id == p_val)
            .filter(Requirement.req_key.like(f"{prefix}%"))
            .all()
        )

        max_num = 0
        for (k,) in keys:
            suffix = k[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

        next_num = max_num + 1
        return f"{prefix}{next_num:02d}"

    # ── Requirement Operations ──────────────────────────────────────────────────

    def get_requirement_by_id(
        self, req_id: str | UUID, project_id: Optional[str | UUID] = None
    ) -> Optional[Requirement]:
        r_val = UUID(str(req_id)) if not isinstance(req_id, UUID) else req_id
        query = (
            self.db.query(Requirement)
            .options(joinedload(Requirement.acceptance_criteria))
            .filter(Requirement.id == r_val)
        )
        if project_id:
            p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
            query = query.filter(Requirement.project_id == p_val)
        return query.first()

    def list_requirements(
        self,
        project_id: str | UUID,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Requirement]:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        query = (
            self.db.query(Requirement)
            .options(joinedload(Requirement.acceptance_criteria))
            .filter(Requirement.project_id == p_val)
        )

        if category:
            query = query.filter(Requirement.category == category)
        if priority:
            query = query.filter(Requirement.priority == priority)
        if status:
            query = query.filter(Requirement.status == status)
        if search:
            search_filter = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Requirement.title.ilike(search_filter),
                    Requirement.description.ilike(search_filter),
                    Requirement.req_key.ilike(search_filter),
                )
            )

        return (
            query.order_by(desc(Requirement.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_requirements(
        self,
        project_id: str | UUID,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        query = self.db.query(func.count(Requirement.id)).filter(Requirement.project_id == p_val)

        if category:
            query = query.filter(Requirement.category == category)
        if priority:
            query = query.filter(Requirement.priority == priority)
        if status:
            query = query.filter(Requirement.status == status)
        if search:
            search_filter = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Requirement.title.ilike(search_filter),
                    Requirement.description.ilike(search_filter),
                    Requirement.req_key.ilike(search_filter),
                )
            )

        return query.scalar() or 0

    def create_requirement(
        self,
        project_id: str | UUID,
        req_key: str,
        title: str,
        description: Optional[str] = None,
        category: str = RequirementCategory.FUNCTIONAL,
        priority: str = RequirementPriority.MEDIUM,
        status: str = RequirementStatus.DRAFT,
        created_by: Optional[str | UUID] = None,
        document_id: Optional[str | UUID] = None,
        criteria_list: Optional[List[str]] = None,
    ) -> Requirement:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        c_val = UUID(str(created_by)) if created_by and not isinstance(created_by, UUID) else created_by
        d_val = UUID(str(document_id)) if document_id and not isinstance(document_id, UUID) else document_id

        req = Requirement(
            project_id=p_val,
            document_id=d_val,
            req_key=req_key,
            title=title.strip(),
            description=description.strip() if description else None,
            category=category,
            priority=priority,
            status=status,
            created_by=c_val,
        )
        self.db.add(req)
        self.db.flush()  # assign req.id

        if criteria_list:
            for idx, text in enumerate(criteria_list):
                if text and text.strip():
                    ac = AcceptanceCriteria(
                        requirement_id=req.id,
                        criteria=text.strip(),
                        order_index=idx,
                    )
                    self.db.add(ac)

        self.db.commit()
        return self.get_requirement_by_id(req.id, p_val)

    def update_requirement(
        self,
        req_id: str | UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        criteria_list: Optional[List[str]] = None,
    ) -> Optional[Requirement]:
        req = self.get_requirement_by_id(req_id)
        if not req:
            return None

        if title is not None:
            req.title = title.strip()
        if description is not None:
            req.description = description.strip() if description else None
        if category is not None:
            req.category = category
        if priority is not None:
            req.priority = priority
        if status is not None:
            req.status = status

        if criteria_list is not None:
            # Replace existing criteria
            self.db.query(AcceptanceCriteria).filter(
                AcceptanceCriteria.requirement_id == req.id
            ).delete()
            for idx, text in enumerate(criteria_list):
                if text and text.strip():
                    ac = AcceptanceCriteria(
                        requirement_id=req.id,
                        criteria=text.strip(),
                        order_index=idx,
                    )
                    self.db.add(ac)

        self.db.commit()
        return self.get_requirement_by_id(req.id)

    def delete_requirement(self, req_id: str | UUID) -> bool:
        req = self.get_requirement_by_id(req_id)
        if not req:
            return False
        self.db.delete(req)
        self.db.commit()
        return True

    # ── Document Operations ─────────────────────────────────────────────────────

    def create_document(
        self,
        project_id: str | UUID,
        uploaded_by: Optional[str | UUID],
        filename: str,
        file_type: str,
        file_size_bytes: int,
        raw_content: Optional[str] = None,
        parsing_status: str = DocParsingStatus.PENDING,
    ) -> RequirementDocument:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        u_val = UUID(str(uploaded_by)) if uploaded_by and not isinstance(uploaded_by, UUID) else uploaded_by

        doc = RequirementDocument(
            project_id=p_val,
            uploaded_by=u_val,
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            raw_content=raw_content,
            parsing_status=parsing_status,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document_by_id(
        self, doc_id: str | UUID, project_id: Optional[str | UUID] = None
    ) -> Optional[RequirementDocument]:
        d_val = UUID(str(doc_id)) if not isinstance(doc_id, UUID) else doc_id
        query = self.db.query(RequirementDocument).filter(RequirementDocument.id == d_val)
        if project_id:
            p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
            query = query.filter(RequirementDocument.project_id == p_val)
        return query.first()

    def update_document_status(self, doc_id: str | UUID, status: str) -> None:
        doc = self.get_document_by_id(doc_id)
        if doc:
            doc.parsing_status = status
            self.db.commit()

    def list_documents(
        self, project_id: str | UUID, skip: int = 0, limit: int = 50
    ) -> List[RequirementDocument]:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        return (
            self.db.query(RequirementDocument)
            .filter(RequirementDocument.project_id == p_val)
            .order_by(desc(RequirementDocument.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
