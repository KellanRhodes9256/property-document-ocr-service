"""Deterministic property-document modeling after OCR extraction."""

from __future__ import annotations

import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class DocumentKind(str, Enum):
    MAINTENANCE_REQUEST = "maintenance_request"
    TENANT_DOCUMENT = "tenant_document"
    INSPECTION_REMINDER = "inspection_reminder"
    UNCATEGORIZED = "uncategorized"


class Priority(str, Enum):
    URGENT = "urgent"
    NORMAL = "normal"


class PropertyDocument(BaseModel):
    kind: DocumentKind
    priority: Priority
    search_text: str = Field(min_length=1)
    inspection_date: date | None = None


_MAINTENANCE_TERMS = ("maintenance", "repair", "work order", "leak", "no heat")
_URGENT_TERMS = ("active leak", "flood", "no heat", "electrical hazard", "gas smell")
_TENANT_TERMS = ("tenant", "lease", "rental agreement", "move-in")
_INSPECTION_TERMS = ("inspection", "inspect", "annual review")
_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def model_property_document(text: str) -> PropertyDocument:
    """Classify normalized OCR text and expose fields useful for search."""
    search_text = " ".join(text.split())
    if not search_text:
        raise ValueError("OCR text must contain at least one non-whitespace character")

    lowered = search_text.casefold()
    priority = Priority.URGENT if any(term in lowered for term in _URGENT_TERMS) else Priority.NORMAL

    if any(term in lowered for term in _MAINTENANCE_TERMS):
        kind = DocumentKind.MAINTENANCE_REQUEST
    elif any(term in lowered for term in _INSPECTION_TERMS):
        kind = DocumentKind.INSPECTION_REMINDER
    elif any(term in lowered for term in _TENANT_TERMS):
        kind = DocumentKind.TENANT_DOCUMENT
    else:
        kind = DocumentKind.UNCATEGORIZED

    inspection_date = None
    if kind is DocumentKind.INSPECTION_REMINDER:
        match = _ISO_DATE.search(search_text)
        if match:
            inspection_date = date.fromisoformat(match.group(1))

    return PropertyDocument(
        kind=kind,
        priority=priority,
        search_text=search_text,
        inspection_date=inspection_date,
    )
