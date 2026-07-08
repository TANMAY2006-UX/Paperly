import statistics
from extractor.models import ExtractionContext, LayoutProfile

def detect_layout(context: ExtractionContext) -> ExtractionContext:
    """
    Stage 4: Per-page Layout Detection (Refactored for Evidence-First)
    
    Publisher Profile -> Prior Confidence Only
    Geometry -> Actual Evidence
    Final Confidence -> Layout Decision
    """
    prior_expected_columns = context.publisher.expected_columns if context.publisher else 1
    
    # 1. Dynamic Header/Footer Detection
    top_candidates = []
    bottom_candidates = []
    
    for p in context.pages:
        blocks = sorted(p.blocks, key=lambda b: b.y0)
        valid_blocks = [b for b in blocks if len(b.text.strip()) > 0]
        
        if len(valid_blocks) >= 2:
            # Header isolation check
            for i in range(len(valid_blocks) - 1):
                b = valid_blocks[i]
                next_b = valid_blocks[i+1]
                if b.y1 > 0.15:
                    break
                if next_b.y0 - b.y1 > 0.03: # Strong vertical isolation
                    total_text_len = sum(len(x.text) for x in valid_blocks[:i+1])
                    if total_text_len < 150: # Significantly less text than a body column
                        top_candidates.append(b.y1)
                    break
                    
            # Footer isolation check
            for i in range(len(valid_blocks) - 1, 0, -1):
                b = valid_blocks[i]
                prev_b = valid_blocks[i-1]
                if b.y0 < 0.85:
                    break
                if b.y0 - prev_b.y1 > 0.03:
                    total_text_len = sum(len(x.text) for x in valid_blocks[i:])
                    if total_text_len < 150:
                        bottom_candidates.append(b.y0)
                    break

    min_evidence = max(2, len(context.pages) // 4)
    
    # Default to 0.0 and 1.0 (no headers/footers) to prevent false positives
    global_header_zone_y = 0.00
    global_footer_zone_y = 1.00
    
    if len(top_candidates) >= min_evidence:
        global_header_zone_y = statistics.median(top_candidates) + 0.005
        
    if len(bottom_candidates) >= min_evidence:
        global_footer_zone_y = statistics.median(bottom_candidates) - 0.005
        
    context.log(
        stage="layout",
        action="dynamic_margins_detected",
        reason=f"Header evidence: {len(top_candidates)}, Footer evidence: {len(bottom_candidates)}",
        details={"header_zone_y": global_header_zone_y, "footer_zone_y": global_footer_zone_y}
    )

    # 2. Page-level Geometric Clustering
    for p in context.pages:
        # Filter obvious noise, but KEEP wide blocks because they might be normal 1-col text!
        valid_blocks = [b for b in p.blocks if len(b.text.strip()) >= 10]
        
        if not valid_blocks:
            p.layout = LayoutProfile(
                column_count=prior_expected_columns,
                header_zone_y=global_header_zone_y,
                footer_zone_y=global_footer_zone_y,
                left_margin=0.0,
                right_margin=1.0,
                confidence=0.0
            )
            continue
            
        x0_positions = [b.x0 for b in valid_blocks]
        
        # Simple geometric clustering
        # Assuming left column starts < 0.45, right column starts >= 0.45
        left_blocks = [x for x in x0_positions if x < 0.45]
        right_blocks = [x for x in x0_positions if x >= 0.45]
        
        has_strong_left = len(left_blocks) >= 3
        has_strong_right = len(right_blocks) >= 3
        
        confidence = 0.0
        
        if has_strong_left and has_strong_right:
            # Evidence of two distinct text streams
            column_count = 2
            confidence = 1.0
        elif has_strong_left and not has_strong_right:
            # Evidence of a single text stream
            column_count = 1
            confidence = 1.0 if len(left_blocks) >= 5 else 0.5
        else:
            # Ambiguous geometry, fall back to publisher prior
            column_count = prior_expected_columns
            confidence = 0.0
            
        column_split_x = None
        if column_count == 2:
            if right_blocks:
                column_split_x = statistics.median(right_blocks) - 0.02
            else:
                column_split_x = 0.500
                
        p.layout = LayoutProfile(
            column_count=column_count,
            column_split_x=column_split_x,
            header_zone_y=global_header_zone_y,
            footer_zone_y=global_footer_zone_y,
            left_margin=min(x0_positions) if x0_positions else 0.08,
            right_margin=max([b.x1 for b in valid_blocks]) if valid_blocks else 0.92,
            confidence=confidence
        )
        
        context.log(
            stage="layout",
            action="page_layout_detected",
            reason=f"Page {p.page_num}: column_count={column_count} with {confidence:.2f} confidence.",
            details={"page_num": p.page_num, "confidence": confidence, "column_count": column_count}
        )
        
    context.log(
        stage="layout",
        action="detect_layout",
        reason="Evidence-first layout detection via x0 clustering completed.",
        details={}
    )
    return context
