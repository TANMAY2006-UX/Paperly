import statistics
from extractor.models import ExtractionContext, LayoutProfile

def detect_layout(context: ExtractionContext) -> ExtractionContext:
    """
    Stage 4: Per-page Layout Detection (Phase G.5 Algorithm)
    
    Implements the frozen Universal Body Region algorithm via 1D Quorum-Filtered Projection Hull.
    """
    prior_expected_columns = context.publisher.expected_columns if context.publisher else 1
    
    N = len(context.pages)
    quorum = max(1, N // 4)
    epsilon = 0.005
    
    # 1. Quorum Filtering (Outlier Rejection)
    bin_count = int(1.0 / epsilon) + 1
    page_bins = [set() for _ in range(bin_count)]
    all_y0s = []
    
    for p in context.pages:
        for b in p.blocks:
            if not b.text.strip(): continue
            all_y0s.append(b.y0)
            
            start_bin = int(max(0.0, b.y0) / epsilon)
            end_bin = int(min(1.0, b.y1) / epsilon)
            for i in range(start_bin, end_bin + 1):
                page_bins[i].add(p.page_num)
                
    # 2. Interval Generation
    intervals = []
    current_start = None
    
    for i in range(bin_count):
        if len(page_bins[i]) >= quorum:
            if current_start is None:
                current_start = i
        else:
            if current_start is not None:
                intervals.append((current_start * epsilon, (i - 1) * epsilon))
                current_start = None
                
    if current_start is not None:
        intervals.append((current_start * epsilon, (bin_count - 1) * epsilon))
        
    # 3. Geometric Merging
    merged_intervals = []
    if intervals:
        intervals.sort()
        current_I = intervals[0]
        
        for next_I in intervals[1:]:
            g = next_I[0] - current_I[1]
            h_A = current_I[1] - current_I[0]
            h_B = next_I[1] - next_I[0]
            
            if g <= min(h_A, h_B) + 1e-5:
                current_I = (current_I[0], max(current_I[1], next_I[1]))
            else:
                merged_intervals.append(current_I)
                current_I = next_I
        merged_intervals.append(current_I)
        
    # 4. Central Mass Selection
    M_top, M_bot = 0.0, 1.0
    if merged_intervals and all_y0s:
        Y_median = statistics.median(all_y0s)
        body_interval = None
        for I in merged_intervals:
            if I[0] <= Y_median <= I[1]:
                body_interval = I
                break
                
        if not body_interval:
            body_interval = min(merged_intervals, key=lambda i: min(abs(i[0]-Y_median), abs(i[1]-Y_median)))
            
        M_top, M_bot = body_interval[0], body_interval[1]
        
    # 5. Furniture Clustering
    candidates = []
    for p in context.pages:
        for b in p.blocks:
            if not b.text.strip(): continue
            if b.y1 < M_top or b.y0 > M_bot:
                candidates.append((p, b))
                
    furn_quorum = max(2, N // 4)
    cluster_epsilon = 0.015
    clusters = []
    for p, b in candidates:
        b_h = b.y1 - b.y0
        matched = False
        for cluster in clusters:
            ref_b = cluster[0][1]
            ref_h = ref_b.y1 - ref_b.y0
            if abs(b.y0 - ref_b.y0) <= cluster_epsilon and abs(b_h - ref_h) <= cluster_epsilon:
                cluster.append((p, b))
                matched = True
                break
        if not matched:
            clusters.append([(p, b)])
            
    furniture_blocks = []
    for cluster in clusters:
        unique_pages = set(c[0].page_num for c in cluster)
        if len(unique_pages) >= furn_quorum:
            for p, b in cluster:
                furniture_blocks.append((p.page_num, b))
                
    # 6. Page Layout and Assignment
    for p in context.pages:
        valid_blocks = [b for b in p.blocks if len(b.text.strip()) >= 10]
        
        if not valid_blocks:
            p.layout = LayoutProfile(
                column_count=prior_expected_columns,
                header_zone_y=M_top,
                footer_zone_y=M_bot,
                page_headers=[],
                page_footers=[],
                left_margin=0.0,
                right_margin=1.0,
                confidence=0.0
            )
            continue
            
        x0_positions = [b.x0 for b in valid_blocks]
        left_blocks = [x for x in x0_positions if x < 0.45]
        right_blocks = [x for x in x0_positions if x >= 0.45]
        
        has_strong_left = len(left_blocks) >= 3
        has_strong_right = len(right_blocks) >= 3
        
        confidence = 0.0
        if has_strong_left and has_strong_right:
            column_count = 2
            confidence = 1.0
        elif has_strong_left and not has_strong_right:
            column_count = 1
            confidence = 1.0 if len(left_blocks) >= 5 else 0.5
        else:
            column_count = prior_expected_columns
            confidence = 0.0
            
        column_split_x = None
        if column_count == 2:
            if right_blocks:
                column_split_x = statistics.median(right_blocks) - 0.02
            else:
                column_split_x = 0.500
                
        page_headers = [b.textblock_id for p_num, b in furniture_blocks if p_num == p.page_num and b.y1 < M_top]
        page_footers = [b.textblock_id for p_num, b in furniture_blocks if p_num == p.page_num and b.y0 > M_bot]
                
        p.layout = LayoutProfile(
            column_count=column_count,
            column_split_x=column_split_x,
            header_zone_y=M_top,
            footer_zone_y=M_bot,
            page_headers=page_headers,
            page_footers=page_footers,
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
        reason="Quorum-Filtered 1D Projection Body Region detection completed.",
        details={"M_top": M_top, "M_bot": M_bot, "furniture_blocks_count": len(furniture_blocks)}
    )
    return context