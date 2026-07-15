import re
from typing import List, Dict, Optional, Set
from enum import Enum, auto

from extractor.models import (
    ExtractionContext, SemanticType, SemanticNode,
    TypographicGroup, LandmarkKind
)
from extractor.telemetry import StageTransitionEvent

class ParserState(Enum):
    INIT = auto()
    TITLE_SEARCH = auto()
    FRONT_MATTER_PARSE = auto()
    BODY_PARSE = auto()
    REFERENCES_PARSE = auto()
    APPENDIX_PARSE = auto()
    END = auto()

def _compute_safe_body_class(context: ExtractionContext, anchor_group_id: Optional[str], ref_group_id: Optional[str]) -> int:
    """
    Computes the universal body class by evaluating groups physically between 
    the Title (ANCHOR) and References (OUTLIER), ignoring suspected captions.
    """
    if not context.assembled_groups:
        return -1
        
    start_idx = 0
    end_idx = len(context.assembled_groups)
    
    # 1. Bound by anchor and ref physically
    if anchor_group_id:
        for i, g in enumerate(context.assembled_groups):
            if g.group_id == anchor_group_id:
                start_idx = i
                break
    if ref_group_id:
        for i, g in enumerate(context.assembled_groups):
            if g.group_id == ref_group_id:
                end_idx = i
                break
                
    body_groups = context.assembled_groups[start_idx:end_idx]
    if not body_groups:
        body_groups = context.assembled_groups
        
    class_lengths: Dict[int, int] = {}
    for group in body_groups:
        text = group.display_text.strip()
        # Ignore caption regex
        if re.match(r'^(?:(?:Supplementary|Extended Data|Appendix)\s+)?(?:Figure|Fig\.?|FIGURE|Table|TABLE)\s+(?:[1-9][0-9]*|[IVXLCDM]+|[A-Z])[\.:]?\s+', text, re.IGNORECASE):
            continue
            
        cls = group.typography_class
        class_lengths[cls] = class_lengths.get(cls, 0) + len(group.display_text)
        
    if not class_lengths:
        return -1
        
    # Class with max character mass
    return max(class_lengths.items(), key=lambda x: x[1])[0]

def _is_caption(group: TypographicGroup) -> bool:
    text = group.display_text.strip()
    return bool(re.match(r'^(?:(?:Supplementary|Extended Data|Appendix)\s+)?(?:Figure|Fig\.?|FIGURE|Table|TABLE)\s+(?:[1-9][0-9]*|[IVXLCDM]+|[A-Z])[\.:]?\s+', text, re.IGNORECASE))

def reconstruct_semantics(context: ExtractionContext) -> ExtractionContext:
    context.emit(StageTransitionEvent(stage_name="SemanticReconstruction", status="START"))
    
    if not context.assembled_groups:
        context.log("SemanticReconstruction", "Skipped", "No input available")
        context.emit(StageTransitionEvent(stage_name="SemanticReconstruction", status="END"))
        return context

    # 1. Initialization and Context Lookups
    anchor_groups: Set[str] = set()
    outlier_groups: Set[str] = set()
    first_anchor_id = None
    first_ref_id = None
    
    if context.landmark_report:
        for token in context.landmark_report.tokens:
            if token.kind == LandmarkKind.ANCHOR:
                anchor_groups.add(token.group_id)
                if not first_anchor_id:
                    first_anchor_id = token.group_id
            elif token.kind == LandmarkKind.OUTLIER:
                outlier_groups.add(token.group_id)
                # Naive pre-scan to bound body class (heuristic only for class computation)
                for g in context.assembled_groups:
                    if g.group_id == token.group_id and not first_ref_id:
                        if re.match(r'^(?:\d+\.?\s*)?References?\s*$', g.display_text.strip(), re.IGNORECASE):
                            first_ref_id = g.group_id
    
    universal_body_class = _compute_safe_body_class(context, first_anchor_id, first_ref_id)
    root = SemanticNode(node_type=SemanticType.DOCUMENT)
    section_stack: List[SemanticNode] = [root]
    state = ParserState.TITLE_SEARCH
    
    # 2. Forward Iteration
    for group in context.assembled_groups:
        is_anchor = group.group_id in anchor_groups
        is_outlier = group.group_id in outlier_groups
        text_lower = group.display_text.lower().strip()
        
        # 3. Transitions
        if state == ParserState.TITLE_SEARCH:
            if is_anchor:
                # Top-level Title found
                section_stack[-1].children.append(SemanticNode(node_type=SemanticType.TITLE, group=group))
                state = ParserState.FRONT_MATTER_PARSE
            else:
                # Pre-title noise or headers
                section_stack[-1].children.append(SemanticNode(node_type=SemanticType.NOISE, group=group))
                continue
                
        elif state == ParserState.FRONT_MATTER_PARSE:
            if is_outlier:
                if re.match(r'^(?:\d+\.?\s*)?abstract\b', text_lower, re.IGNORECASE):
                    abs_node = SemanticNode(node_type=SemanticType.ABSTRACT, group=group)
                    root.children.append(abs_node)
                    section_stack.append(abs_node)
                    continue
                elif section_stack[-1].node_type == SemanticType.ABSTRACT or re.match(r'^(?:\d+\.?|[IVXLCDM]+\.?)\s+', text_lower) or re.match(r'^(?:introduction|background|motivation)\b', text_lower):
                    # An OUTLIER in front matter that is structurally verified implies start of BODY
                    state = ParserState.BODY_PARSE
                    # Re-evaluate this group under BODY_PARSE rules
                else:
                    # An unproven OUTLIER defaults to AUTHORS fallback
                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.AUTHORS, group=group))
                    continue
            else:
                if section_stack[-1].node_type == SemanticType.ABSTRACT:
                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.PARAGRAPH, group=group))
                else:
                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.AUTHORS, group=group))
                    
        if state == ParserState.BODY_PARSE:
            if is_outlier:
                if re.match(r'^(?:\d+\.?\s*)?References?\s*$', text_lower):
                    state = ParserState.REFERENCES_PARSE
                    # Re-evaluate under REFERENCES_PARSE
                elif re.match(r'^(?:\d+\.?\s*)?Appendices|Appendix\b', text_lower):
                    state = ParserState.APPENDIX_PARSE
                    # Re-evaluate under APPENDIX_PARSE
                elif group.typography_class == universal_body_class:
                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.PARAGRAPH, group=group))
                elif _is_caption(group):
                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.CAPTION, group=group))
                else:
                    # Body Section Header Resolution
                    while len(section_stack) > 1:
                        top_section = section_stack[-1]
                        header_group = None
                        for child in top_section.children:
                            if child.node_type == SemanticType.SECTION_HEADER:
                                header_group = child.group
                                break
                                
                        # Using mathematical magnitude: smaller typography_class ID means physically larger text
                        if header_group and group.typography_class > header_group.typography_class:
                            break # New header is smaller structurally (larger class id), push as nested child
                        section_stack.pop() # Ascend hierarchy (sibling or parent)
                        
                    new_section = SemanticNode(node_type=SemanticType.SECTION)
                    new_section.children.append(SemanticNode(node_type=SemanticType.SECTION_HEADER, group=group))
                    section_stack[-1].children.append(new_section)
                    section_stack.append(new_section)
            else:
                if _is_caption(group):
                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.CAPTION, group=group))
                else:
                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.PARAGRAPH, group=group))
                
        elif state == ParserState.REFERENCES_PARSE:
            if is_outlier and re.match(r'^(?:\d+\.?\s*)?Appendices|Appendix\b', text_lower):
                state = ParserState.APPENDIX_PARSE
                # Re-evaluate
            elif is_outlier:
                # Non-appendix outlier inside references... might be a new reference block or noise
                while len(section_stack) > 1:
                    section_stack.pop()
                new_section = SemanticNode(node_type=SemanticType.REFERENCES)
                new_section.children.append(SemanticNode(node_type=SemanticType.SECTION_HEADER, group=group))
                section_stack[-1].children.append(new_section)
                section_stack.append(new_section)
            else:
                section_stack[-1].children.append(SemanticNode(node_type=SemanticType.REFERENCES, group=group))
                
        if state == ParserState.APPENDIX_PARSE:
            if is_outlier:
                while len(section_stack) > 1:
                    section_stack.pop()
                new_section = SemanticNode(node_type=SemanticType.APPENDIX)
                new_section.children.append(SemanticNode(node_type=SemanticType.SECTION_HEADER, group=group))
                section_stack[-1].children.append(new_section)
                section_stack.append(new_section)
            else:
                section_stack[-1].children.append(SemanticNode(node_type=SemanticType.PARAGRAPH, group=group))

    context.semantic_tree = root
    
    # Recursively count nodes for logging
    def count_nodes(node: SemanticNode) -> int:
        return 1 + sum(count_nodes(child) for child in node.children)
        
    node_count = count_nodes(root)
    
    context.log(
        stage="SemanticReconstruction",
        action="reconstruct_semantics",
        reason=f"Constructed DAG with {node_count} nodes (UBC: {universal_body_class})."
    )
    
    context.emit(StageTransitionEvent(stage_name="SemanticReconstruction", status="END"))
    return context
