import re
from typing import List, Tuple, Optional
from extractor.telemetry import DecisionEvent, StageTransitionEvent
from extractor.models import (
    ExtractionContext,
    TypographicGroup,
    FenceType,
    AnchorType,
    ConfidenceStrength,
    EvidenceCategory,
    LandmarkEvidence,
    StructuralFence,
    DocumentAnchor,
    LandmarkReport
)

# --- Regex Patterns ---
# Explicit headers
ABSTRACT_PAT = re.compile(r"^(abstract|Zusammenfassung|Résumé)\b", re.IGNORECASE)
REFERENCES_PAT = re.compile(r"^(references|bibliography)\b", re.IGNORECASE)
APPENDIX_PAT = re.compile(r"^appendix\b", re.IGNORECASE)
ACKNOWLEDGEMENTS_PAT = re.compile(r"^(acknowledgments|acknowledgements)\b", re.IGNORECASE)

# Sections: 1. Introduction, I. Introduction, 1 Introduction
SECTION_PAT = re.compile(r"^((?:[1-9][0-9]*|[IVXLCDM]+)(?:\.[0-9]+)*)\.?\s+([A-Z][A-Za-z\s]+)$")

# Anchors
KEYWORDS_PAT = re.compile(r"^(index\s*terms|keywords)(?:\s*:|\b)", re.IGNORECASE)
CCS_PAT = re.compile(r"^(ccs\s*concepts|categories\s*and\s*subject\s*descriptors)(?:\s*:|\b)", re.IGNORECASE)
EMAIL_PAT = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def detect_landmarks(context: ExtractionContext) -> ExtractionContext:
    context.emit(StageTransitionEvent(stage_name="Landmarks", status="START"))
    fences: List[StructuralFence] = []
    anchors: List[DocumentAnchor] = []
    
    # 1. Structural Fences
    fences.extend(_detect_abstract_fences(context))
    fences.extend(_detect_references_fences(context))
    fences.extend(_detect_appendix_fences(context))
    fences.extend(_detect_acknowledgements_fences(context))
    fences.extend(_detect_section_fences(context))
    
    # 2. Document Anchors
    anchors.extend(_detect_title_candidates(context))
    anchors.extend(_detect_keywords(context))
    anchors.extend(_detect_ccs(context))
    anchors.extend(_detect_emails(context))
    
    total_confidence = 0.0
    total_count = len(fences) + len(anchors)
    if total_count > 0:
        total_confidence = sum(f.confidence_score for f in fences) + sum(a.confidence_score for a in anchors)
        avg_confidence = total_confidence / total_count
    else:
        avg_confidence = 0.0
        
    report = LandmarkReport(
        fences=fences,
        anchors=anchors,
        average_confidence=avg_confidence
    )
    
    context.landmark_report = report
    context.emit(StageTransitionEvent(stage_name="Landmarks", status="END"))
    context.log("LandmarkDetection", "Detected landmarks", f"Found {len(fences)} fences and {len(anchors)} anchors")
    
    return context


def _detect_abstract_fences(context: ExtractionContext) -> List[StructuralFence]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        if ABSTRACT_PAT.match(g.display_text.strip()):
            evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches ABSTRACT regex", 1.0)]
            if g.is_bold:
                evidence.append(LandmarkEvidence(EvidenceCategory.TYPOGRAPHY, "Is bold", 0.1))
                
            fence = StructuralFence(
                group_ids=[g.group_id],
                confidence_score=1.0,
                confidence_strength=ConfidenceStrength.EXACT,
                dominant_category=EvidenceCategory.REGEX,
                evidence_ledger=evidence,
                page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                reading_order_start=i,
                fence_type=FenceType.ABSTRACT_HEADING
            )
            res.append(fence)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', fence.confidence_score, 'Matches target criteria'))
    return res

def _detect_references_fences(context: ExtractionContext) -> List[StructuralFence]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        text = g.display_text.strip()
        if REFERENCES_PAT.match(text):
            if len(text) < 50:
                evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches REFERENCES regex", 1.0)]
                if g.is_bold:
                    evidence.append(LandmarkEvidence(EvidenceCategory.TYPOGRAPHY, "Is bold", 0.1))
                
                fence = StructuralFence(
                    group_ids=[g.group_id],
                    confidence_score=1.0,
                    confidence_strength=ConfidenceStrength.EXACT,
                    dominant_category=EvidenceCategory.REGEX,
                    evidence_ledger=evidence,
                    page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                    reading_order_start=i,
                    fence_type=FenceType.REFERENCES_HEADING
                )
                res.append(fence)
                context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', fence.confidence_score, 'Matches target criteria'))
            else:
                context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'REJECTED', 0.0, f'Length {len(text)} >= 50'))
    return res

def _detect_appendix_fences(context: ExtractionContext) -> List[StructuralFence]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        text = g.display_text.strip()
        if APPENDIX_PAT.match(text):
            if len(text) < 100:
                evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches APPENDIX regex", 1.0)]
                fence = StructuralFence(
                    group_ids=[g.group_id],
                    confidence_score=1.0,
                    confidence_strength=ConfidenceStrength.EXACT,
                    dominant_category=EvidenceCategory.REGEX,
                    evidence_ledger=evidence,
                    page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                    reading_order_start=i,
                    fence_type=FenceType.APPENDIX_HEADING
                )
                res.append(fence)
                context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', fence.confidence_score, 'Matches target criteria'))
            else:
                context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'REJECTED', 0.0, f'Length {len(text)} >= 100'))
    return res

def _detect_acknowledgements_fences(context: ExtractionContext) -> List[StructuralFence]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        text = g.display_text.strip()
        if ACKNOWLEDGEMENTS_PAT.match(text):
            if len(text) < 100:
                evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches ACKNOWLEDGEMENTS regex", 1.0)]
                fence = StructuralFence(
                    group_ids=[g.group_id],
                    confidence_score=1.0,
                    confidence_strength=ConfidenceStrength.EXACT,
                    dominant_category=EvidenceCategory.REGEX,
                    evidence_ledger=evidence,
                    page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                    reading_order_start=i,
                    fence_type=FenceType.ACKNOWLEDGEMENTS_HEADING
                )
                res.append(fence)
                context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', fence.confidence_score, 'Matches target criteria'))
            else:
                context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'REJECTED', 0.0, f'Length {len(text)} >= 100'))
    return res

def _detect_section_fences(context: ExtractionContext) -> List[StructuralFence]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        text = g.display_text.strip()
        
        match = SECTION_PAT.match(text)
        if match:
            if len(text) >= 150:
                context.emit(DecisionEvent('Landmarks', g.group_id, 'SECTION_REGEX', 'REJECTED', 0.0, f'Length {len(text)} >= 150'))
                continue
                
            evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches numbered section pattern", 0.8)]
            confidence = 0.8
            strength = ConfidenceStrength.HIGH
            
            if g.is_bold:
                evidence.append(LandmarkEvidence(EvidenceCategory.TYPOGRAPHY, "Is bold", 0.15))
                confidence += 0.15
                strength = ConfidenceStrength.EXACT
                
            fence = StructuralFence(
                group_ids=[g.group_id],
                confidence_score=min(1.0, confidence),
                confidence_strength=strength,
                dominant_category=EvidenceCategory.REGEX,
                evidence_ledger=evidence,
                page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                reading_order_start=i,
                fence_type=FenceType.SECTION_HEADING
            )
            res.append(fence)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', fence.confidence_score, 'Matches target criteria'))
            continue
            
        # Unnumbered bold sections
        # Needs to be short, bold, not purely uppercase (or maybe yes), not starting with lower case
        if g.is_bold and 3 < len(text) < 60 and not text.islower() and text.istitle():
            # Filter out non-sections
            if any(p.match(text) for p in [ABSTRACT_PAT, REFERENCES_PAT, APPENDIX_PAT, ACKNOWLEDGEMENTS_PAT]):
                context.emit(DecisionEvent('Landmarks', g.group_id, 'UNNUMBERED_BOLD', 'VETOED', 0.0, 'Matched explicit fence pattern'))
                continue
                
            evidence = [
                LandmarkEvidence(EvidenceCategory.TYPOGRAPHY, "Short bold title-case text", 0.6),
                LandmarkEvidence(EvidenceCategory.POSITION, "Potential unnumbered section", 0.1)
            ]
            
            fence = StructuralFence(
                group_ids=[g.group_id],
                confidence_score=0.7,
                confidence_strength=ConfidenceStrength.MEDIUM,
                dominant_category=EvidenceCategory.TYPOGRAPHY,
                evidence_ledger=evidence,
                page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                reading_order_start=i,
                fence_type=FenceType.SECTION_HEADING
            )
            res.append(fence)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', fence.confidence_score, 'Matches target criteria'))
            
    return res

def _detect_title_candidates(context: ExtractionContext) -> List[DocumentAnchor]:
    groups = context.assembled_groups
    # Title is usually the largest font on the first page, near the top
    page0_groups = [g for g in groups if g.source_blocks and g.source_blocks[0].page_num == 0]
    if not page0_groups:
        return []
        
    max_size = max(g.dominant_size for g in page0_groups)
    candidates = [g for g in page0_groups if g.dominant_size >= max_size - 0.5]
    
    for g in page0_groups:
        if g not in candidates and g.dominant_size >= max_size - 2.0:
            context.emit(DecisionEvent('Landmarks', g.group_id, 'TITLE_GEOMETRY', 'REJECTED', 0.0, f'Font {g.dominant_size} smaller than max {max_size}'))
            
    # Sort by vertical position
    candidates.sort(key=lambda g: g.y0)
    
    res = []
    # If a title is split across multiple typographic groups (e.g. CVPR huge titles), they should be contiguous
    # Let's find contiguous blocks of max_size
    current_title_groups = []
    start_i = -1
    
    for i, g in enumerate(groups):
        if g in candidates:
            if not current_title_groups:
                start_i = i
            current_title_groups.append(g)
        else:
            if current_title_groups:
                # Issue the anchor
                evidence = [
                    LandmarkEvidence(EvidenceCategory.GEOMETRY, "Largest font on page 1", 0.9),
                    LandmarkEvidence(EvidenceCategory.POSITION, "First page, top portion", 0.1)
                ]
                anchor = DocumentAnchor(
                    group_ids=[cg.group_id for cg in current_title_groups],
                    confidence_score=1.0,
                    confidence_strength=ConfidenceStrength.HIGH,
                    dominant_category=EvidenceCategory.GEOMETRY,
                    evidence_ledger=evidence,
                    page_num=0,
                    reading_order_start=start_i,
                    anchor_type=AnchorType.TITLE_CANDIDATE
                )
                res.append(anchor)
                for cg in current_title_groups:
                    context.emit(DecisionEvent('Landmarks', cg.group_id, 'TITLE_GEOMETRY', 'ACCEPTED', anchor.confidence_score, 'Largest font on page 1'))
                current_title_groups = []
                
    if current_title_groups:
        evidence = [
            LandmarkEvidence(EvidenceCategory.GEOMETRY, "Largest font on page 1", 0.9),
            LandmarkEvidence(EvidenceCategory.POSITION, "First page, top portion", 0.1)
        ]
        anchor = DocumentAnchor(
            group_ids=[cg.group_id for cg in current_title_groups],
            confidence_score=1.0,
            confidence_strength=ConfidenceStrength.HIGH,
            dominant_category=EvidenceCategory.GEOMETRY,
            evidence_ledger=evidence,
            page_num=0,
            reading_order_start=start_i,
            anchor_type=AnchorType.TITLE_CANDIDATE
        )
        res.append(anchor)
        for cg in current_title_groups:
            context.emit(DecisionEvent('Landmarks', cg.group_id, 'TITLE_GEOMETRY', 'ACCEPTED', anchor.confidence_score, 'Largest font on page 1'))
        
    return res

def _detect_keywords(context: ExtractionContext) -> List[DocumentAnchor]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        if KEYWORDS_PAT.search(g.display_text):
            evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches keywords pattern", 0.9)]
            anchor = DocumentAnchor(
                group_ids=[g.group_id],
                confidence_score=0.9,
                confidence_strength=ConfidenceStrength.HIGH,
                dominant_category=EvidenceCategory.REGEX,
                evidence_ledger=evidence,
                page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                reading_order_start=i,
                anchor_type=AnchorType.KEYWORDS_BLOCK
            )
            res.append(anchor)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', anchor.confidence_score, 'Matches target criteria'))
    return res

def _detect_ccs(context: ExtractionContext) -> List[DocumentAnchor]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        if CCS_PAT.search(g.display_text):
            evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches CCS Concepts pattern", 0.9)]
            anchor = DocumentAnchor(
                group_ids=[g.group_id],
                confidence_score=0.9,
                confidence_strength=ConfidenceStrength.HIGH,
                dominant_category=EvidenceCategory.REGEX,
                evidence_ledger=evidence,
                page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                reading_order_start=i,
                anchor_type=AnchorType.CCS_CONCEPTS_BLOCK
            )
            res.append(anchor)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', anchor.confidence_score, 'Matches target criteria'))
    return res

def _detect_emails(context: ExtractionContext) -> List[DocumentAnchor]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        if EMAIL_PAT.search(g.display_text):
            evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Contains email address", 0.8)]
            anchor = DocumentAnchor(
                group_ids=[g.group_id],
                confidence_score=0.8,
                confidence_strength=ConfidenceStrength.HIGH,
                dominant_category=EvidenceCategory.REGEX,
                evidence_ledger=evidence,
                page_num=g.source_blocks[0].page_num if g.source_blocks else -1,
                reading_order_start=i,
                anchor_type=AnchorType.CORRESPONDENCE_EMAIL
            )
            res.append(anchor)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'ACCEPTED', anchor.confidence_score, 'Matches target criteria'))
    return res
