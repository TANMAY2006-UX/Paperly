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
    quality_reports: Dict[str, 'StageQualityReport'] = field(default_factory=dict)
    
    # Output of Stage 1
    assembled_groups: List['TypographicGroup'] = field(default_factory=list)
    
    # Output of Phase 3A.2 Step 1
    landmark_report: Optional['LandmarkReport'] = None
    
    # Telemetry
    telemetry_enabled: bool = False
    event_bus: Any = None
    
    def emit(self, event: Any) -> None:
        if self.telemetry_enabled and self.event_bus:
            self.event_bus.dispatch(event)

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

# --- Stage 1: Typographic Assembly Models ---

@dataclass(slots=True)
class EvidenceVector:
    """Detailed evidence ledger for why two blocks were assembled."""
    vertical_evidence: float = 0.0
    horizontal_evidence: float = 0.0
    font_evidence: float = 0.0
    hyphen_evidence: float = 0.0
    total_confidence: float = 0.0
    reasoning_summary: str = ""

class AssemblyPolicy(Enum):
    CONSERVATIVE = auto()  # Strongly prefers false negatives
    BALANCED = auto()      # Even tradeoff
    AGGRESSIVE = auto()    # Strongly prefers false positives (e.g. for noisy scans)

@dataclass(slots=True)
class ParticipationPolicy:
    """Decides if a block participates in neighborhood graphing. Ignored blocks remain in provenance."""
    min_width_pt: float = 2.0
    min_height_pt: float = 2.0
    min_chars: int = 1
    ignore_noise_type: bool = True

@dataclass(slots=True)
class TypographicGroup:
    """
    A purely visual grouping of raw typographic fragments.
    No semantic meaning is inferred at this stage.
    """
    group_id: str
    
    # Text
    raw_text: str             # Exact text from source blocks, concatenated
    display_text: str         # Text after structural repairs (e.g. hyphen joining)
    
    # Geometry (Bounding box completely enclosing children)
    x0: float
    y0: float
    x1: float
    y1: float
    
    # Typography
    dominant_font: str
    dominant_size: float
    is_bold: bool
    
    # Provenance
    source_blocks: List[TextBlock] = field(default_factory=list)
    
    # Audit
    evidence_vector: EvidenceVector = field(default_factory=EvidenceVector)
    repair_history: List[str] = field(default_factory=list)

@dataclass(slots=True)
class StageQualityReport:
    """Audit report generated by every pipeline stage."""
    stage_name: str
    raw_block_count: int
    participating_blocks: int
    ignored_blocks: int
    assembled_groups: int
    average_confidence: float
    minimum_confidence: float
    maximum_confidence: float
    fragmentation_ratio: float  # assembled_groups / participating_blocks
    warnings: List[str] = field(default_factory=list)

# --- Phase 3A.2 Step 1: Landmark Detection Models ---

class FenceType(Enum):
    ABSTRACT_HEADING = auto()
    SECTION_HEADING = auto()
    REFERENCES_HEADING = auto()
    APPENDIX_HEADING = auto()
    ACKNOWLEDGEMENTS_HEADING = auto()

class AnchorType(Enum):
    TITLE_CANDIDATE = auto()
    KEYWORDS_BLOCK = auto()
    CCS_CONCEPTS_BLOCK = auto()
    PUBLICATION_INFO = auto()
    CORRESPONDENCE_EMAIL = auto()

class ConfidenceStrength(Enum):
    EXACT = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()

class EvidenceCategory(Enum):
    REGEX = auto()
    TYPOGRAPHY = auto()
    GEOMETRY = auto()
    POSITION = auto()
    COMPOSITE = auto()

@dataclass(slots=True)
class LandmarkEvidence:
    category: EvidenceCategory
    reason: str
    score_delta: float

@dataclass(slots=True)
class DetectedLandmark:
    """Base class for Fences and Anchors"""
    group_ids: List[str]
    confidence_score: float
    confidence_strength: ConfidenceStrength
    dominant_category: EvidenceCategory
    evidence_ledger: List[LandmarkEvidence] = field(default_factory=list)
    page_num: int = -1
    reading_order_start: int = -1
    
    # We do NOT store mutable text here. To get the text, resolve group_ids against ExtractionContext.assembled_groups.

@dataclass(slots=True)
class StructuralFence(DetectedLandmark):
    fence_type: FenceType = FenceType.SECTION_HEADING

@dataclass(slots=True)
class DocumentAnchor(DetectedLandmark):
    anchor_type: AnchorType = AnchorType.TITLE_CANDIDATE

@dataclass(slots=True)
class LandmarkReport:
    fences: List[StructuralFence]
    anchors: List[DocumentAnchor]
    average_confidence: float

# --- Phase 3A.1: Semantic Reconstruction Models ---


class SemanticType(Enum):
    TITLE = auto()
    AUTHORS = auto()
    AFFILIATIONS = auto()
    ABSTRACT = auto()
    KEYWORDS = auto()
    FRONT_MATTER = auto()
    SECTION_HEADER = auto()
    SUBSECTION_HEADER = auto()
    PARAGRAPH = auto()
    FIGURE_CAPTION = auto()
    TABLE_CAPTION = auto()
    EQUATION = auto()
    EQUATION_LABEL = auto()
    FOOTNOTE = auto()
    REFERENCES = auto()
    APPENDIX = auto()
    ACKNOWLEDGEMENTS = auto()
    NOISE = auto()

@dataclass(slots=True)
class SemanticBlock:
    """
    A semantic annotation layered on top of a frozen TextBlock.
    Never modifies the source block — only references it.
    """
    source_block: TextBlock
    semantic_type: SemanticType
    confidence: float
    reason: str
    section_id: Optional[str] = None
    reading_order: int = 0

@dataclass(slots=True)
class SectionNode:
    """
    A logical section of the paper, containing classified blocks.
    """
    section_id: str
    heading: SemanticBlock
    level: int
    blocks: List[SemanticBlock] = field(default_factory=list)

@dataclass(slots=True)
class DocumentCorpus:
    """
    Document-level statistics computed in Pass 1.
    """
    body_font_size: float
    body_font_name: str
    title_font_size: float
    is_bold_font: bool
    running_header_set: set

@dataclass(slots=True)
class SemanticDocument:
    """
    The final output of Phase 3A.1.
    """
    slug: str
    title: Optional[SemanticBlock]
    authors: List[SemanticBlock]
    affiliations: List[SemanticBlock]
    abstract: Optional[SemanticBlock]
    keywords: Optional[SemanticBlock]
    sections: List[SectionNode]
    figures: List[SemanticBlock]
    tables: List[SemanticBlock]
    equations: List[SemanticBlock]
    footnotes: List[SemanticBlock]
    references: List[SemanticBlock]
    appendices: List[SectionNode]
    acknowledgements: Optional[SemanticBlock]
    reading_order: List[SemanticBlock]
    audit_log: List[Dict[str, Any]]
