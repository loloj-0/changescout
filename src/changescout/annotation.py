# src/changescout/annotation.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AnnotationRecord:
    document_id: str
    source_id: str
    url: str
    title: str
    clean_text: str
    tlm_relevant: bool
    review_required: bool
    notes: str = ""
    change_type: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.document_id, str) or not self.document_id:
            raise ValueError("document_id must be a non-empty string")

        if not isinstance(self.source_id, str) or not self.source_id:
            raise ValueError("source_id must be a non-empty string")

        if not isinstance(self.url, str) or not self.url:
            raise ValueError("url must be a non-empty string")

        if not isinstance(self.title, str):
            raise ValueError("title must be a string")

        if not isinstance(self.clean_text, str) or not self.clean_text:
            raise ValueError("clean_text must be a non-empty string")

        if not isinstance(self.tlm_relevant, bool):
            raise ValueError("tlm_relevant must be a boolean")

        if not isinstance(self.review_required, bool):
            raise ValueError("review_required must be a boolean")

        if not isinstance(self.notes, str):
            raise ValueError("notes must be a string")

        if self.change_type is not None and self.change_type not in {
            "topology",
            "minor_geometry",
            "none",
        }:
            raise ValueError("invalid change_type")