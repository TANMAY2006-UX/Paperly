import re
from typing import List, Dict, Optional
from extractor.models import (
    ExtractionContext, DocumentZone, ZoneType, SemanticBlock, SemanticType, 
    FenceType, AnchorType, TypographicGroup, LandmarkReport
)
from extractor.telemetry import StageTransitionEvent, DecisionEvent
from extractor import confidence

class ZoneStrategy:
    """Base class for all Zone-Constrained Parsers."""
    def __init__(self, context: ExtractionContext):
        self.context = context
        self.landmark_report = context.landmark_report
        
    def _emit_decision(self, group: TypographicGroup, status: str, score: float, reason: str):
        self.context.emit(DecisionEvent(
            stage_name="SemanticReconstruction",
            group_id=group.group_id,
            evaluator=self.__class__.__name__,
            status=status,
            score=score,
            reason=reason
        ))

    def process(self, zone: DocumentZone) -> List[SemanticBlock]:
        raise NotImplementedError

class FrontMatterStrategy(ZoneStrategy):
    def process(self, zone: DocumentZone) -> List[SemanticBlock]:
        blocks = []
        
        # Build maps for O(1) landmark lookups
        title_anchor_groups = set()
        keyword_anchor_groups = set()
        if self.landmark_report:
            for anchor in self.landmark_report.anchors:
                if anchor.anchor_type == AnchorType.TITLE_CANDIDATE:
                    title_anchor_groups.update(anchor.group_ids)
                elif anchor.anchor_type == AnchorType.KEYWORDS_BLOCK:
                    keyword_anchor_groups.update(anchor.group_ids)
                    
        abstract_fence_groups = set()
        if self.landmark_report:
            for fence in self.landmark_report.fences:
                if fence.fence_type == FenceType.ABSTRACT_HEADING:
                    abstract_fence_groups.update(fence.group_ids)

        found_title = False
        found_abstract = False
        
        for group in zone.groups:
            sem_type = SemanticType.FRONT_MATTER
            score = confidence.TITLE_FALLBACK_THRESHOLD
            reason = "Front-Matter generic fallback"
            
            text_lower = group.display_text.lower()
            
            if group.group_id in title_anchor_groups:
                sem_type = SemanticType.TITLE
                score = confidence.TITLE_THRESHOLD
                reason = "Mapped from Landmark TITLE_CANDIDATE"
                found_title = True
                
            elif group.group_id in abstract_fence_groups:
                sem_type = SemanticType.ABSTRACT
                score = confidence.ABSTRACT_THRESHOLD
                reason = "Mapped from Landmark ABSTRACT_HEADING"
                found_abstract = True
                
            elif group.group_id in keyword_anchor_groups or text_lower.startswith("keywords") or text_lower.startswith("index terms"):
                sem_type = SemanticType.KEYWORDS
                score = confidence.KEYWORD_THRESHOLD
                reason = "Mapped from Landmark KEYWORDS_BLOCK or fallback regex"
                
            elif text_lower.startswith("abstract"):
                sem_type = SemanticType.ABSTRACT
                score = confidence.ABSTRACT_THRESHOLD
                reason = "Implicit abstract detected via regex"
                found_abstract = True
                
            elif found_title and not found_abstract:
                # Positional heuristic: between title and abstract
                # Check for institutions
                has_institution = bool(re.search(r'\b(university|institute|inc|corp|lab|research|department)\b', text_lower)) or "@" in text_lower
                
                if has_institution:
                    sem_type = SemanticType.AFFILIATIONS
                    score = confidence.AFFILIATION_THRESHOLD
                    reason = "Positional heuristic (between Title/Abstract) + Institution keywords"
                else:
                    word_count = len(group.display_text.split())
                    if word_count < 30 and not re.search(r'\b(we|our|this|paper|presents|propose|can|use)\b', text_lower):
                        sem_type = SemanticType.AUTHORS
                        score = confidence.AUTHOR_THRESHOLD
                        reason = "Positional heuristic (between Title/Abstract) + non-prose formatting"
                        
            # Create SemanticBlock wrapping TypographicGroup
            blocks.append(SemanticBlock(
                source_group=group,
                semantic_type=sem_type,
                confidence=score,
                reason=reason,
                reading_order=0
            ))
            self._emit_decision(group, "ACCEPTED", score, f"Assigned {sem_type.name}: {reason}")
            
        return blocks

class BodyStrategy(ZoneStrategy):
    def process(self, zone: DocumentZone) -> List[SemanticBlock]:
        blocks = []
        
        section_fence_groups = set()
        if self.landmark_report:
            for fence in self.landmark_report.fences:
                if fence.fence_type == FenceType.SECTION_HEADING:
                    section_fence_groups.update(fence.group_ids)
                    
        for group in zone.groups:
            sem_type = SemanticType.PARAGRAPH
            score = 0.5  # Neutral base confidence for paragraph fallback
            reason = "Body zone paragraph fallback"
            
            text = group.display_text.strip()
            
            if group.group_id in section_fence_groups:
                sem_type = SemanticType.SECTION_HEADER
                score = confidence.HEADER_THRESHOLD
                reason = "Mapped from Landmark SECTION_HEADING"
                
            elif re.match(r'^(?:(?:Supplementary|Extended Data|Appendix)\s+)?(?:Figure|Fig\.?|FIGURE)\s+(?:[1-9][0-9]*|[IVXLCDM]+|[A-Z])[\.:]?\s+', text, re.IGNORECASE):
                sem_type = SemanticType.FIGURE_CAPTION
                score = confidence.FIGURE_CAPTION_THRESHOLD
                reason = "Regex match for Figure caption"
                
            elif re.match(r'^(?:(?:Supplementary|Extended Data|Appendix)\s+)?(?:Table|TABLE)\s+(?:[1-9][0-9]*|[IVXLCDM]+|[A-Z])[\.:]?\s+', text, re.IGNORECASE):
                sem_type = SemanticType.TABLE_CAPTION
                score = confidence.TABLE_CAPTION_THRESHOLD
                reason = "Regex match for Table caption"
                
            blocks.append(SemanticBlock(
                source_group=group,
                semantic_type=sem_type,
                confidence=score,
                reason=reason,
                reading_order=0
            ))
            self._emit_decision(group, "ACCEPTED", score, f"Assigned {sem_type.name}: {reason}")
            
        return blocks

class BackMatterStrategy(ZoneStrategy):
    def process(self, zone: DocumentZone) -> List[SemanticBlock]:
        blocks = []
        
        is_references = (zone.zone_type == ZoneType.REFERENCES)
        is_appendix = (zone.zone_type == ZoneType.APPENDIX)
        is_acknowledgements = (zone.zone_type == ZoneType.ACKNOWLEDGEMENTS)
        
        fallback_type = SemanticType.NOISE
        if is_references:
            fallback_type = SemanticType.REFERENCES
        elif is_appendix:
            fallback_type = SemanticType.APPENDIX
        elif is_acknowledgements:
            fallback_type = SemanticType.ACKNOWLEDGEMENTS
            
        fence_groups = set()
        if self.landmark_report:
            for fence in self.landmark_report.fences:
                fence_groups.update(fence.group_ids)
                
        for group in zone.groups:
            sem_type = fallback_type
            score = confidence.REFERENCE_THRESHOLD if is_references else 0.70
            reason = f"Back-Matter zone fallback ({zone.zone_type.name})"
            
            if group.group_id in fence_groups:
                sem_type = SemanticType.SECTION_HEADER
                score = confidence.HEADER_THRESHOLD
                reason = "Mapped from Landmark Back-Matter Heading"
                
            blocks.append(SemanticBlock(
                source_group=group,
                semantic_type=sem_type,
                confidence=score,
                reason=reason,
                reading_order=0
            ))
            self._emit_decision(group, "ACCEPTED", score, f"Assigned {sem_type.name}: {reason}")
            
        return blocks

def reconstruct_semantics(context: ExtractionContext) -> ExtractionContext:
    """
    Milestone 4 & 5: Semantic Reconstruction.
    Maps frozen zones and landmarks into semantic blocks without altering geometry.
    """
    context.emit(StageTransitionEvent(stage_name="SemanticReconstruction", status="START"))
    
    if not context.zonal_partition or not context.zonal_partition.zones:
        context.log("SemanticReconstruction", "Skipped", "No ZonalPartition available")
        context.emit(StageTransitionEvent(stage_name="SemanticReconstruction", status="END"))
        return context
        
    front_matter_strategy = FrontMatterStrategy(context)
    body_strategy = BodyStrategy(context)
    back_matter_strategy = BackMatterStrategy(context)
    
    semantic_blocks = []
    
    for zone in context.zonal_partition.zones:
        if zone.zone_type == ZoneType.FRONT_MATTER:
            blocks = front_matter_strategy.process(zone)
            semantic_blocks.extend(blocks)
        elif zone.zone_type == ZoneType.BODY:
            blocks = body_strategy.process(zone)
            semantic_blocks.extend(blocks)
        elif zone.zone_type in (ZoneType.REFERENCES, ZoneType.APPENDIX, ZoneType.ACKNOWLEDGEMENTS):
            blocks = back_matter_strategy.process(zone)
            semantic_blocks.extend(blocks)
        else: # UNKNOWN zone fallback
            blocks = body_strategy.process(zone) # treat UNKNOWN as BODY for fallback resilience
            semantic_blocks.extend(blocks)
            
    # Attach flat list to context (Tree Assembly will organize them later)
    context.semantic_blocks = semantic_blocks
        
    context.log(
        stage="SemanticReconstruction",
        action="reconstruct_semantics",
        reason=f"Classified {len(semantic_blocks)} groups strictly constrained by their zones."
    )
    
    context.emit(StageTransitionEvent(stage_name="SemanticReconstruction", status="END"))
    return context
