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

def _compute_evidence(b1: TextBlock, b2: TextBlock, policy: AssemblyPolicy) -> EvidenceVector:
    """Computes the evidence vector for merging b1 and b2."""
    ev = EvidenceVector()
    
    # 0. Hard constraints
    if b1.page_num != b2.page_num:
        ev.reasoning_summary = "cross-page"
        return ev
        
    # Hard constraint: Structural Line Break
    w1 = b1.x1 - b1.x0
    w2 = b2.x1 - b2.x0

    center1 = (b1.x0 + b1.x1) / 2.0
    center2 = (b2.x0 + b2.x1) / 2.0
    is_centered = abs(center1 - center2) < 0.03
    
    b1_vcenter = (b1.y0 + b1.y1) / 2.0
    b2_vcenter = (b2.y0 + b2.y1) / 2.0
    b1_height = b1.y1 - b1.y0
    is_inline = abs(b1_vcenter - b2_vcenter) < (b1_height * 0.5)

    is_short_line = w1 < (w2 * 0.75)

    if is_short_line and not is_centered and not b1.text.strip().endswith('-') and not is_inline:
        ev.reasoning_summary = "structural line break"
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
    import re
    x_diff = abs(b1.x0 - b2.x0)
    if x_diff < 0.02:
        ev.horizontal_evidence = 0.2
    elif b2.x0 > b1.x0 and b2.x0 - b1.x0 < 0.05:
        # typical indent
        ev.horizontal_evidence = 0.15
    elif re.match(r'^(?:[1-9][0-9]*|[IVXLCDM]+|[A-Z])(?:\.[0-9]+)*\.?$', b1.text.strip()) and vertical_gap <= b1.size * 0.1 and b1.y0 <= b2.y0 and b1.y1 >= b2.y1:
        # Tab-stop assembly rule for purely enumerated labels
        ev.horizontal_evidence = 0.8
        
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
        ev.reasoning_summary = "passed threshold"
    else:
        ev.reasoning_summary = f"failed threshold ({ev.total_confidence:.2f} < {threshold})"
        
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
    
    for block in participating_blocks:
        if not current_cluster:
            current_cluster.append(block)
            continue
            
        last_block = current_cluster[-1]
        ev = _compute_evidence(last_block, block, policy)
        
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
