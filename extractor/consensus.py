import statistics
from extractor.models import ExtractionContext, DocumentLayout, DocumentLayoutKind, BlockType

def detect_consensus(context: ExtractionContext) -> ExtractionContext:
    """
    Stage 4b: Document Layout Consensus
    Determines DocumentLayoutKind and primary_split_x based on evidence from pages,
    incorporating publisher priors and gutter tolerance.
    """
    if not context.pages:
        return context

    # 1. Collect votes and priors
    votes = [] # list of (column_count, split_x)
    anomaly_pages = []
    
    prior_columns = context.publisher.expected_columns if context.publisher else 1

    for p in context.pages:
        layout = p.layout
        # Confidence-based filtering
        if layout.confidence >= 0.8:
            votes.append((layout.column_count, layout.column_split_x))
        else:
            anomaly_pages.append(p.page_num)

    # 2. Add publisher prior into consensus voting
    # Provide weight to publisher's expectation
    prior_weight = 2
    for _ in range(prior_weight):
        votes.append((prior_columns, None))

    # 3. Majority Consensus for Column Count
    col_counts = [v[0] for v in votes]
    if not col_counts:
        primary_columns = prior_columns
    else:
        count_freq = {}
        for c in col_counts:
            count_freq[c] = count_freq.get(c, 0) + 1
        primary_columns = max(count_freq.keys(), key=lambda k: count_freq[k])

    kind = DocumentLayoutKind.SINGLE_COLUMN
    if primary_columns == 2:
        kind = DocumentLayoutKind.DOUBLE_COLUMN
        
    # 4. Gutter calculation with tolerance
    primary_split_x = None
    if kind == DocumentLayoutKind.DOUBLE_COLUMN:
        valid_splits = [v[1] for v in votes if v[0] == 2 and v[1] is not None]
        if valid_splits:
            primary_split_x = statistics.median(valid_splits)

    # 5. Confidence scoring
    agreeing_votes = len([v for v in votes if v[0] == primary_columns])
    doc_confidence = agreeing_votes / len(votes) if votes else 0.0

    context.document_layout = DocumentLayout(
        kind=kind,
        primary_split_x=primary_split_x,
        confidence=doc_confidence,
        anomaly_pages=anomaly_pages
    )

    # 6. Second pass: Apply DocumentLayout to PageBlocks
    for p in context.pages:
        for b in p.blocks:
            if len(b.text.strip()) < 10:
                b.block_type = BlockType.NOISE
                continue
            
            width_ratio = b.x1 - b.x0
            if kind == DocumentLayoutKind.DOUBLE_COLUMN:
                # Tolerance check for spanning (e.g. > 0.8 width)
                if width_ratio > 0.8:
                    b.spans_columns = True
            
            if not b.spans_columns and b.block_type == BlockType.NOISE:
                b.block_type = BlockType.PARAGRAPH # Tentative baseline for now

    context.log(
        stage="consensus",
        action="detect_consensus",
        reason="Calculated DocumentLayout from page votes and priors.",
        details={
            "kind": kind.name,
            "confidence": doc_confidence,
            "primary_split_x": primary_split_x
        }
    )
    return context
