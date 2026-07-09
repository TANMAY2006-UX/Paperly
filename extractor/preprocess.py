import uuid
from typing import List, Dict, Any, Tuple
from extractor.models import (
    ExtractionContext, 
    TextBlock, 
    TypographicGroup, 
    EvidenceVector, 
    AssemblyPolicy, 
    ParticipationPolicy,
    StageQualityReport,
    BlockType
)

def _is_bold(font_name: str, flags: int) -> bool:
    if flags & 16:
        return True
    font_lower = font_name.lower()
    return any(indicator in font_lower for indicator in ["bold", "-bd", "heavy", "black", "demi", "medi"])

def _evaluate_flush(b1: TextBlock, b2: TextBlock, layout: 'LayoutProfile') -> bool:
    return abs(b1.x0 - b2.x0) <= 0.02

def _evaluate_centered(b1: TextBlock, b2: TextBlock, layout: 'LayoutProfile') -> bool:
    center1 = (b1.x0 + b1.x1) / 2.0
    center2 = (b2.x0 + b2.x1) / 2.0
    return abs(center1 - center2) <= 0.03

def _evaluate_hanging(b1: TextBlock, b2: TextBlock, layout: 'LayoutProfile') -> bool:
    return b2.x0 - b1.x0 > 0.02 and b2.x0 - b1.x0 <= 0.15

def _evaluate_paragraph_indent(b1: TextBlock, b2: TextBlock, layout: 'LayoutProfile') -> bool:
    return b1.x0 - b2.x0 > 0.02 and b1.x0 - b2.x0 <= 0.15

def evaluate_horizontal_continuity(b1: TextBlock, b2: TextBlock, layout: 'LayoutProfile') -> Tuple[float, str]:
    if _evaluate_flush(b1, b2, layout):
        return (0.20, "+Horizontal(Flush)")
    if _evaluate_centered(b1, b2, layout):
        return (0.20, "+Horizontal(Centered)")
    if _evaluate_paragraph_indent(b1, b2, layout):
        return (0.20, "+Horizontal(Indent)")
    if _evaluate_hanging(b1, b2, layout):
        return (0.20, "+Horizontal(Hanging)")
    return (0.0, "")

def _compute_evidence(b1: TextBlock, b2: TextBlock, policy: AssemblyPolicy, layout: 'LayoutProfile' = None) -> EvidenceVector:
    """
    Computes the evidence vector for merging b1 and b2.

    layout: the LayoutProfile for the page, used to derive column widths and centers
    for structural invariants (Hard Line Break, Centered Continuation).
    """
    ev = EvidenceVector()
    
    # 0. Hard constraints
    if b1.page_num != b2.page_num:
        ev.reasoning_summary = "cross-page"
        return ev

    # Hard constraint: Structural Line Break (Phase 3D — Approved Invariant)
    b1_width = b1.x1 - b1.x0
    has_trailing_hyphen = b1.text.strip().endswith('-')

    column_width = 0.0
    if layout:
        if layout.column_count == 2 and layout.column_split_x is not None:
            column_width = layout.column_split_x - layout.left_margin
        else:
            column_width = layout.right_margin - layout.left_margin

    if column_width > 0.0:
        is_short_line = b1_width < column_width * 0.6
        is_new_line_start = b2.x0 < b1_width * 1.2
        
        # Centered Continuation Invariant (Phase E)
        # If both blocks are geometrically centered relative to each other AND
        # relative to the page or column, they form a centered primitive and
        # should bypass the structural line break veto.
        center1 = (b1.x0 + b1.x1) / 2.0
        center2 = (b2.x0 + b2.x1) / 2.0
        is_mutually_centered = abs(center1 - center2) < 0.03
        
        is_geometrically_centered = False
        if is_mutually_centered:
            page_center = (layout.left_margin + layout.right_margin) / 2.0
            if abs(center1 - page_center) < 0.05:
                is_geometrically_centered = True
            elif layout.column_count == 2 and layout.column_split_x is not None:
                left_col_center = (layout.left_margin + layout.column_split_x) / 2.0
                right_col_center = (layout.column_split_x + layout.right_margin) / 2.0
                if abs(center1 - left_col_center) < 0.05 or abs(center1 - right_col_center) < 0.05:
                    is_geometrically_centered = True

        if is_short_line and not has_trailing_hyphen and is_new_line_start and not is_geometrically_centered:
            ev.reasoning_summary = "structural line break (column-width gate)"
            return ev
    else:
        # Fallback when layout is unavailable: relative comparison

        # (temporary; should not occur after layout detection runs)
        w2 = b2.x1 - b2.x0
        center1 = (b1.x0 + b1.x1) / 2.0
        center2 = (b2.x0 + b2.x1) / 2.0
        is_centered = abs(center1 - center2) < 0.03
        b1_vcenter = (b1.y0 + b1.y1) / 2.0
        b2_vcenter = (b2.y0 + b2.y1) / 2.0
        b1_height = b1.y1 - b1.y0
        is_inline = abs(b1_vcenter - b2_vcenter) < (b1_height * 0.5)
        is_short_line = b1_width < (w2 * 0.75)
        if is_short_line and not is_centered and not has_trailing_hyphen and not is_inline:
            ev.reasoning_summary = "structural line break (relative fallback)"
            return ev
    
    vertical_gap = b2.y0 - b1.y1
    
    # Negative gap means overlap. Allow slight overlap.
    if vertical_gap < - (b1.size * 0.5):
        pass
        
    font_size_ratio = max(b1.size, b2.size) / min(b1.size, b2.size) if min(b1.size, b2.size) > 0 else 999
    
    # 1. Vertical Proximity
    if vertical_gap > b1.size * 2.5:
        ev.reasoning_summary = "large vertical gap"
        return ev
        
    if vertical_gap <= b1.size * 1.5 and vertical_gap > - (b1.size * 0.2):
        ev.vertical_evidence = 0.4 * (1.0 - max(0, vertical_gap / (b1.size * 1.5)))
    elif vertical_gap <= 0 and b1.y0 <= b2.y0 and b1.y1 >= b2.y1:
        # b2 is inline with b1
        ev.vertical_evidence = 0.4
        
    # 2. Font Continuity
    if b1.font == b2.font and abs(b1.size - b2.size) < 0.5:
        ev.font_evidence = 0.3
    elif abs(b1.size - b2.size) < 1.0:
        ev.font_evidence = 0.15
        
    # 3. Horizontal Alignment
    h_score, h_reason = evaluate_horizontal_continuity(b1, b2, layout)
    ev.horizontal_evidence = h_score
    if h_reason:
        ev.reasoning_summary = (ev.reasoning_summary + " " if ev.reasoning_summary else "") + h_reason
        
    x_diff = abs(b1.x0 - b2.x0)
    # 4. Hyphenation Proof
    if b1.text.strip().endswith('-'):
        if x_diff < 0.02:  # B2 starts at same margin
            ev.hyphen_evidence = 0.3
            
    # Compute total
    ev.total_confidence = ev.vertical_evidence + ev.horizontal_evidence + ev.font_evidence + ev.hyphen_evidence
    ev.total_confidence = min(1.0, ev.total_confidence)
    
    # Assembly Policy Thresholds
    threshold = 0.85
    if policy == AssemblyPolicy.AGGRESSIVE:
        threshold = 0.65
    elif policy == AssemblyPolicy.BALANCED:
        threshold = 0.75
        
    if ev.total_confidence >= threshold:
        ev.reasoning_summary = (ev.reasoning_summary + " (passed)" if ev.reasoning_summary else "passed threshold")
    else:
        ev.reasoning_summary = (ev.reasoning_summary + " " if ev.reasoning_summary else "") + f"failed threshold ({ev.total_confidence:.2f} < {threshold})"

        
    return ev

def assemble_typographic_groups(
    ordered_blocks: List[TextBlock],
    context: ExtractionContext,
    policy: AssemblyPolicy = AssemblyPolicy.CONSERVATIVE,
    part_policy: ParticipationPolicy = ParticipationPolicy()
) -> ExtractionContext:
    """
    Stage 1: Typographic Assembly
    Converts ordered raw blocks into composite TypographicGroups.
    """
    
    groups = []
    ignored_blocks = []
    
    # 1. Filter participating blocks
    participating_blocks = []
    for b in ordered_blocks:
        width_pt = (b.x1 - b.x0) * context.pages[b.page_num].width if context.pages else 0
        height_pt = (b.y1 - b.y0) * context.pages[b.page_num].height if context.pages else 0
        
        if (width_pt < part_policy.min_width_pt or 
            height_pt < part_policy.min_height_pt or 
            len(b.text.strip()) < part_policy.min_chars):
            ignored_blocks.append(b)
            continue
            
        if part_policy.ignore_noise_type and b.block_type in (BlockType.NOISE, BlockType.PAGE_HEADER, BlockType.PAGE_FOOTER):
            ignored_blocks.append(b)
            continue
            
        participating_blocks.append(b)
        
    # 2. Neighborhood Graphing & Clustering
    current_cluster: List[TextBlock] = []
    cluster_evidence = EvidenceVector()
    
    min_confidence = 1.0
    max_confidence = 0.0
    total_confidence_sum = 0.0
    assembly_count = 0
    
    def finalize_cluster(cluster: List[TextBlock], ev: EvidenceVector):
        nonlocal min_confidence, max_confidence, total_confidence_sum, assembly_count
        if not cluster:
            return
            
        x0 = min(b.x0 for b in cluster)
        y0 = min(b.y0 for b in cluster)
        x1 = max(b.x1 for b in cluster)
        y1 = max(b.y1 for b in cluster)
        
        font_mass = {}
        size_mass = {}
        bold_mass = 0
        total_mass = 0
        
        raw_text_parts = []
        display_text_parts = []
        repair_history = []
        
        for i, b in enumerate(cluster):
            mass = len(b.text)
            total_mass += mass
            font_mass[b.font] = font_mass.get(b.font, 0) + mass
            size_mass[b.size] = size_mass.get(b.size, 0) + mass
            if _is_bold(b.font, b.flags):
                bold_mass += mass
                
            raw_text_parts.append(b.text)
            
            text = b.text.strip()
            if i > 0:
                prev_text = cluster[i-1].text.strip()
                if prev_text.endswith('-'):
                    display_text_parts[-1] = display_text_parts[-1][:-1]
                    repair_history.append(f"Removed hyphen between block {cluster[i-1].block_num} and {b.block_num}")
                    display_text_parts.append(text)
                else:
                    display_text_parts.append(" " + text)
            else:
                display_text_parts.append(text)
                
        dominant_font = max(font_mass.items(), key=lambda x: x[1])[0] if font_mass else "Unknown"
        dominant_size = max(size_mass.items(), key=lambda x: x[1])[0] if size_mass else 10.0
        is_bold = (bold_mass / total_mass) > 0.5 if total_mass > 0 else False
        
        if len(cluster) > 1:
            assembly_count += 1
            total_confidence_sum += ev.total_confidence
            min_confidence = min(min_confidence, ev.total_confidence)
            max_confidence = max(max_confidence, ev.total_confidence)
        else:
            ev.total_confidence = 1.0
            ev.reasoning_summary = "isolated block"
            
        group = TypographicGroup(
            group_id=str(uuid.uuid4())[:8],
            raw_text="\n".join(raw_text_parts),
            display_text="".join(display_text_parts),
            x0=x0, y0=y0, x1=x1, y1=y1,
            dominant_font=dominant_font,
            dominant_size=dominant_size,
            is_bold=is_bold,
            source_blocks=cluster.copy(),
            evidence_vector=ev,
            repair_history=repair_history
        )
        groups.append(group)
    
    # Build a page → LayoutProfile lookup
    page_layouts = {p.page_num: p.layout for p in context.pages if p.layout}

    for block in participating_blocks:
        if not current_cluster:
            current_cluster.append(block)
            continue
            
        last_block = current_cluster[-1]
        layout = page_layouts.get(last_block.page_num)
        ev = _compute_evidence(last_block, block, policy, layout=layout)

        
        threshold = 0.85
        if policy == AssemblyPolicy.AGGRESSIVE: threshold = 0.65
        elif policy == AssemblyPolicy.BALANCED: threshold = 0.75
            
        if ev.total_confidence >= threshold:
            current_cluster.append(block)
            if len(current_cluster) == 2:
                cluster_evidence = ev
            else:
                cluster_evidence.total_confidence = min(cluster_evidence.total_confidence, ev.total_confidence)
                cluster_evidence.vertical_evidence = min(cluster_evidence.vertical_evidence, ev.vertical_evidence)
                cluster_evidence.horizontal_evidence = min(cluster_evidence.horizontal_evidence, ev.horizontal_evidence)
        else:
            finalize_cluster(current_cluster, cluster_evidence)
            current_cluster = [block]
            cluster_evidence = EvidenceVector()
            
    if current_cluster:
        finalize_cluster(current_cluster, cluster_evidence)
        
    avg_conf = total_confidence_sum / assembly_count if assembly_count > 0 else 1.0
    if min_confidence == 1.0 and assembly_count == 0: min_confidence = 1.0
    
    report = StageQualityReport(
        stage_name="Typographic Assembly",
        raw_block_count=len(ordered_blocks),
        participating_blocks=len(participating_blocks),
        ignored_blocks=len(ignored_blocks),
        assembled_groups=len(groups),
        average_confidence=avg_conf,
        minimum_confidence=min_confidence,
        maximum_confidence=max_confidence,
        fragmentation_ratio=len(groups) / len(participating_blocks) if participating_blocks else 0,
        warnings=[]
    )
    
    if report.fragmentation_ratio > 0.9 and len(participating_blocks) > 50:
        report.warnings.append("High fragmentation ratio. Blocks are not merging. Is PDF scanned or policy too conservative?")
        
    context.assembled_groups = groups
    context.quality_reports["Stage1_Assembly"] = report
    
    context.log(
        stage="assembly",
        action="assemble_typographic_groups",
        reason=f"Assembled {len(participating_blocks)} blocks into {len(groups)} groups using {policy.name} policy.",
        details={"groups": len(groups), "avg_confidence": avg_conf}
    )
    
    return context
