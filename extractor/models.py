from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum, auto

class DocumentLayoutKind(Enum):
    SINGLE_COLUMN = auto()
    DOUBLE_COLUMN = auto()
    HYBRID = auto()

class BlockType(Enum):
    TITLE = auto()
    AUTHORS = auto()
    ABSTRACT = auto()
    SECTION_HEADER = auto()
    PARAGRAPH = auto()
    FIGURE = auto()
    TABLE = auto()
    EQUATION = auto()
    FOOTNOTE = auto()
    REFERENCES = auto()
    NOISE = auto()

@dataclass(slots=True)
class DocumentLayout:
    kind: DocumentLayoutKind
    primary_split_x: Optional[float]
    confidence: float
    anomaly_pages: List[int] = field(default_factory=list)

@dataclass(slots=True)
class TextBlock:
    """
    The atomic unit of text extraction.
    Immutable after normalization.
    Coordinates are normalized (0.0 to 1.0) relative to page dimensions.
    """
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font: str
    size: float
    flags: int
    page_num: int
    block_num: int
    spans_columns: bool = False
    block_type: BlockType = field(default=BlockType.NOISE)

@dataclass(slots=True)
class LayoutProfile:
    """
    The physical layout constraints detected for a specific page.
    """
    column_count: int
    header_zone_y: float
    footer_zone_y: float
    left_margin: float
    right_margin: float
    column_split_x: Optional[float] = None
    confidence: float = 1.0

@dataclass(slots=True)
class PageBlocks:
    """
    A container for all blocks on a single page, plus its physical layout.
    """
    page_num: int
    width: float
    height: float
    blocks: List[TextBlock] = field(default_factory=list)
    layout: Optional[LayoutProfile] = None

@dataclass(slots=True)
class PublisherProfile:
    """
    The semantic rules for a venue (e.g. ACM, IEEE).
    """
    name: str
    expected_columns: int
    has_mixed_layout: bool
    header_patterns: List[str] = field(default_factory=list)
    section_numbering: str = "numeric"

@dataclass(slots=True)
class ExtractionContext:
    """
    The state object passed through the pipeline stages.
    """
    pdf_path: str
    slug: str
    publisher: Optional[PublisherProfile] = None
    pages: List[PageBlocks] = field(default_factory=list)
    document_layout: Optional[DocumentLayout] = None
    audit_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def log(self, stage: str, action: str, reason: str, details: Optional[Dict[str, Any]] = None):
        """Helper to append to the audit log."""
        entry = {
            "stage": stage,
            "action": action,
            "reason": reason
        }
        if details:
            entry.update(details)
        self.audit_log.append(entry)
