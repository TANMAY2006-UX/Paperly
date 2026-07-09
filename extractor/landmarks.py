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
SECTION_PAT = re.compile(r"^((?:[1-9][0-9]*|[IVXLCDM]+)(?:\.[0-9]+)*)\.?\s+([A-Z0-9][A-Za-z0-9\s\-\(\):/,\.]+)")

# Anchors
KEYWORDS_PAT = re.compile(r"^(index\s*terms|keywords)(?:\s*:|\b)", re.IGNORECASE)
CCS_PAT = re.compile(r"^(ccs\s*concepts|categories\s*and\s*subject\s*descriptors)(?:\s*:|\b)", re.IGNORECASE)
EMAIL_PAT = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Universal Sections (Fallback for unnumbered bold headers)
UNIVERSAL_SECTIONS_PAT = re.compile(r"^(introduction|background|related work|method|methodology|experiments|results|discussion|conclusion|evaluation)\b", re.IGNORECASE)


def detect_landmarks(context: ExtractionContext) -> ExtractionContext:
    context.emit(StageTransitionEvent(stage_name="Landmarks", status="START"))
    fences: List[StructuralFence] = []
    anchors: List[DocumentAnchor] = []
    
    # 1. Document Anchors (Needed by Fences for mutual exclusion)
    anchors.extend(_detect_title_candidates(context))
    anchors.extend(_detect_keywords(context))
    anchors.extend(_detect_ccs(context))
    anchors.extend(_detect_emails(context))
    
    # 2. Structural Fences
    fences.extend(_detect_abstract_fences(context))
    fences.extend(_detect_references_fences(context))
    fences.extend(_detect_appendix_fences(context))
    fences.extend(_detect_acknowledgements_fences(context))
    fences.extend(_detect_section_fences(context, anchors))
    
    # Priority 4: Implicit Boundaries
    has_abstract = any(f.fence_type == FenceType.ABSTRACT_HEADING for f in fences)
    section_fences = [f for f in fences if f.fence_type == FenceType.SECTION_HEADING]
    
    title_anchor_idx = -1
    for a in anchors:
        if a.anchor_type == AnchorType.TITLE_CANDIDATE:
            title_anchor_idx = max(title_anchor_idx, a.reading_order_start)

    # 4a. Implicit Abstract (if missing, use first section)
    if not has_abstract and section_fences:
        first_section = min(section_fences, key=lambda f: f.reading_order_start)
        idx = first_section.reading_order_start - 1
        
        if idx > title_anchor_idx:  # Refinement 2: Protect the title
            g = context.assembled_groups[idx]
            evidence = [LandmarkEvidence(EvidenceCategory.POSITION, "Implicit abstract boundary before first section", 0.5)]
            implicit_abstract = StructuralFence(
                group_ids=[g.group_id],
                confidence_score=0.5,
                confidence_strength=ConfidenceStrength.MEDIUM,
                dominant_category=EvidenceCategory.POSITION,
                evidence_ledger=evidence,
                page_num=g.source_blocks[0].page_num if g.source_blocks else getattr(g, 'page_num', -1),
                reading_order_start=idx,
                fence_type=FenceType.ABSTRACT_HEADING
            )
            fences.append(implicit_abstract)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'IMPLICIT_ABSTRACT', 'ACCEPTED', 0.5, "Implicit abstract boundary before first section"))

    # 4b. Body Prose Start (Refinement 1) - If no section headings exist, we MUST inject one to start the BODY zone
    if not section_fences:
        abstract_anchor_idx = -1
        for f in fences:
            if f.fence_type == FenceType.ABSTRACT_HEADING:
                abstract_anchor_idx = max(abstract_anchor_idx, f.reading_order_start)
                
        from collections import Counter
        font_counts = Counter()
        size_counts = Counter()
        for g in context.assembled_groups:
            font_counts[g.dominant_font] += len(g.display_text)
            size_counts[g.dominant_size] += len(g.display_text)
        
        if font_counts and size_counts:
            dom_font = font_counts.most_common(1)[0][0]
            dom_size = size_counts.most_common(1)[0][0]
            
            # Dynamically determine the full column width for the body font
            body_widths = [g.x1 - g.x0 for g in context.assembled_groups if abs(g.dominant_size - dom_size) < 0.5]
            max_width = max(body_widths) if body_widths else 0.80
            min_width = max_width * 0.80
            
            idx = -1
            for i, g in enumerate(context.assembled_groups):
                if i <= title_anchor_idx or i <= abstract_anchor_idx:
                    continue
                    
                is_dom_font = (g.dominant_font == dom_font)
                is_dom_size = abs(g.dominant_size - dom_size) < 0.5
                is_full_width = (g.x1 - g.x0) > min_width
                
                if is_dom_font and is_dom_size and is_full_width:
                    idx = i
                    break
                    
            if idx > title_anchor_idx:
                g = context.assembled_groups[idx]
                evidence = [LandmarkEvidence(EvidenceCategory.POSITION, "Body prose start fallback", 0.5)]
                
                # We inject a SECTION_HEADING so that zones.py transitions to BODY.
                # If we also lack an abstract, inject an ABSTRACT_HEADING immediately prior.
                if not has_abstract and (idx - 1) > title_anchor_idx:
                    prev_g = context.assembled_groups[idx - 1]
                    implicit_abstract = StructuralFence(
                        group_ids=[prev_g.group_id],
                        confidence_score=0.5,
                        confidence_strength=ConfidenceStrength.MEDIUM,
                        dominant_category=EvidenceCategory.POSITION,
                        evidence_ledger=evidence,
                        page_num=prev_g.source_blocks[0].page_num if prev_g.source_blocks else getattr(prev_g, 'page_num', -1),
                        reading_order_start=idx - 1,
                        fence_type=FenceType.ABSTRACT_HEADING
                    )
                    fences.append(implicit_abstract)
                    context.emit(DecisionEvent('Landmarks', prev_g.group_id, 'IMPLICIT_ABSTRACT', 'ACCEPTED', 0.5, "Implicit abstract boundary before body prose start"))
                
                implicit_section = StructuralFence(
                    group_ids=[g.group_id],
                    confidence_score=0.5,
                    confidence_strength=ConfidenceStrength.MEDIUM,
                    dominant_category=EvidenceCategory.POSITION,
                    evidence_ledger=evidence,
                    page_num=g.source_blocks[0].page_num if g.source_blocks else getattr(g, 'page_num', -1),
                    reading_order_start=idx,
                    fence_type=FenceType.SECTION_HEADING
                )
                fences.append(implicit_section)
                context.emit(DecisionEvent('Landmarks', g.group_id, 'IMPLICIT_SECTION', 'ACCEPTED', 0.5, "Implicit section boundary at body prose start"))
    
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

def _detect_section_fences(context: ExtractionContext, anchors: List[DocumentAnchor]) -> List[StructuralFence]:
    groups = context.assembled_groups
    res = []
    for i, g in enumerate(groups):
        text = g.display_text.strip()
        
        match = SECTION_PAT.match(text)
        if match:
            evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches numbered section pattern", 0.8)]
            confidence = 0.8
            strength = ConfidenceStrength.HIGH
            
            if g.is_bold:
                evidence.append(LandmarkEvidence(EvidenceCategory.TYPOGRAPHY, "Is bold", 0.15))
                confidence += 0.15
                strength = ConfidenceStrength.EXACT
                
            if len(text) >= 150:
                context.emit(DecisionEvent('Landmarks', g.group_id, 'REGEX_MATCHER', 'REJECTED', 0.0, f'Run-in header detected (length {len(text)} >= 150)'))
                continue
                
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
            
        # Unnumbered bold sections fallback replacement
        if UNIVERSAL_SECTIONS_PAT.match(text) and len(text) < 80:
            
            # Mutual Exclusion: Must not be part of a TITLE_CANDIDATE
            is_title = any(g.group_id in a.group_ids for a in anchors if a.anchor_type == AnchorType.TITLE_CANDIDATE)
            if is_title:
                context.emit(DecisionEvent('Landmarks', g.group_id, 'UNIVERSAL_SECTION', 'VETOED', 0.0, 'Mutual exclusion: Group is a TITLE_CANDIDATE'))
                continue
                
            evidence = [LandmarkEvidence(EvidenceCategory.REGEX, "Matches universal unnumbered section pattern", 0.8)]
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
                page_num=g.source_blocks[0].page_num if g.source_blocks else getattr(g, 'page_num', -1),
                reading_order_start=i,
                fence_type=FenceType.SECTION_HEADING
            )
            res.append(fence)
            context.emit(DecisionEvent('Landmarks', g.group_id, 'UNIVERSAL_SECTION', 'ACCEPTED', fence.confidence_score, 'Matches target criteria'))
        else:
            if g.is_bold and 3 < len(text) < 80:
                context.emit(DecisionEvent('Landmarks', g.group_id, 'UNNUMBERED_BOLD', 'REJECTED', 0.0, 'Blind typography fallback removed'))
            
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
    
    # Merge contiguous max_size groups
    if not candidates:
        return res
        
    merged_titles = []
    current_title = [candidates[0]]
    
    for i in range(1, len(candidates)):
        curr_group = candidates[i]
        prev_group = candidates[i-1]
        
        # Check if they are contiguous vertically
        vertical_gap = curr_group.y0 - prev_group.y1
        if vertical_gap < prev_group.dominant_size * 2.0:
            current_title.append(curr_group)
        else:
            merged_titles.append(current_title)
            current_title = [curr_group]
            
    if current_title:
        merged_titles.append(current_title)
        
    for title_groups in merged_titles:
        evidence = [
            LandmarkEvidence(EvidenceCategory.GEOMETRY, "Maximum font size on Page 0", 0.9),
            LandmarkEvidence(EvidenceCategory.POSITION, "First page, top portion", 0.1)
        ]
        anchor = DocumentAnchor(
            group_ids=[cg.group_id for cg in title_groups],
            confidence_score=1.0,
            confidence_strength=ConfidenceStrength.HIGH,
            dominant_category=EvidenceCategory.GEOMETRY,
            evidence_ledger=evidence,
            page_num=0,
            reading_order_start=groups.index(current_title[0]),
            anchor_type=AnchorType.TITLE_CANDIDATE
        )
        res.append(anchor)
        for cg in current_title:
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
