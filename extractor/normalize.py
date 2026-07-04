from extractor.models import ExtractionContext, TextBlock

LIGATURE_MAP = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
}

def resolve_ligatures(text: str) -> str:
    """Resolve standard PDF ligatures to standard characters."""
    for lig, replacement in LIGATURE_MAP.items():
        if lig in text:
            text = text.replace(lig, replacement)
    return text

def normalize_context(context: ExtractionContext) -> ExtractionContext:
    """
    Stage 2: Normalize coordinates and resolve ligatures.
    Removes blocks with invalid bounding boxes.
    """
    total_corrected = 0
    total_removed = 0
    
    for pb in context.pages:
        normalized_blocks = []
        for b in pb.blocks:
            # 1. Coordinate normalization (0.0 to 1.0)
            nx0 = b.x0 / pb.width
            ny0 = b.y0 / pb.height
            nx1 = b.x1 / pb.width
            ny1 = b.y1 / pb.height
            
            # 2. Filter zero-area blocks or invalid bounding boxes
            if nx0 >= nx1 or ny0 >= ny1:
                total_removed += 1
                continue
                
            # 3. Ligature resolution
            old_text = b.text
            new_text = resolve_ligatures(old_text)
            if old_text != new_text:
                total_corrected += 1
                
            if not new_text.strip():
                total_removed += 1
                continue
                
            # Create a new, normalized TextBlock (maintaining immutability of the old one)
            normalized_tb = TextBlock(
                text=new_text,
                x0=nx0,
                y0=ny0,
                x1=nx1,
                y1=ny1,
                font=b.font,
                size=b.size,
                flags=b.flags,
                page_num=b.page_num,
                block_num=b.block_num
            )
            normalized_blocks.append(normalized_tb)
            
        pb.blocks = normalized_blocks
        
    context.log(
        stage="normalize",
        action="normalize_coordinates_and_ligatures",
        reason="Convert coordinates to 0.0-1.0 relative to page bounds and resolve standard PDF ligatures.",
        details={"ligatures_resolved": total_corrected, "blocks_removed": total_removed}
    )
    return context
