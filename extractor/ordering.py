from typing import List
from extractor.models import ExtractionContext, TextBlock, DocumentLayoutKind

def compute_reading_order(context: ExtractionContext) -> List[TextBlock]:
    """
    Computes a stable, human-like reading order for all blocks in the document.
    This is a pure permutation. Input blocks == output blocks. No deletions.
    """
    ordered_blocks = []
    
    # We use the global split_x for two-column pages unless it's missing
    global_split_x = None
    if context.document_layout and context.document_layout.primary_split_x is not None:
        global_split_x = context.document_layout.primary_split_x
        
    for page in context.pages:
        if not page.layout:
            # Fallback if no layout profile exists
            ordered_blocks.extend(sorted(page.blocks, key=lambda b: (b.y0, b.x0)))
            continue
            
        header_y = page.layout.header_zone_y
        footer_y = page.layout.footer_zone_y
        
        # 1. Headers (at the very top of the page sequence)
        headers = [b for b in page.blocks if b.y0 <= header_y]
        headers.sort(key=lambda b: (b.y0, b.x0))
        ordered_blocks.extend(headers)
        
        # 2. Body blocks
        body_blocks = [b for b in page.blocks if b.y0 > header_y and b.y0 < footer_y]
        
        col_count = page.layout.column_count
        
        if col_count == 1:
            body_blocks.sort(key=lambda b: (b.y0, b.x0))
            ordered_blocks.extend(body_blocks)
        else:
            # DOUBLE_COLUMN
            split_x = global_split_x if global_split_x is not None else (page.layout.column_split_x or 0.5)
            
            # Find spanning blocks in the body
            spanners = [b for b in body_blocks if b.spans_columns]
            spanners.sort(key=lambda b: b.y0)
            
            non_spanners = [b for b in body_blocks if not b.spans_columns]
            
            # Divide the page into vertical bands defined by spanning blocks
            current_y = header_y
            
            for spanner in spanners:
                # Blocks above this spanner
                band_blocks = [b for b in non_spanners if b.y0 >= current_y and b.y0 < spanner.y0]
                
                # Sort left column then right column
                left_col = [b for b in band_blocks if b.x0 < split_x]
                right_col = [b for b in band_blocks if b.x0 >= split_x]
                
                left_col.sort(key=lambda b: (b.y0, b.x0))
                right_col.sort(key=lambda b: (b.y0, b.x0))
                
                ordered_blocks.extend(left_col)
                ordered_blocks.extend(right_col)
                
                # Then the spanner itself
                ordered_blocks.append(spanner)
                
                current_y = spanner.y1
                
            # Remaining blocks below the last spanner (or all blocks if no spanners)
            band_blocks = [b for b in non_spanners if b.y0 >= current_y]
            left_col = [b for b in band_blocks if b.x0 < split_x]
            right_col = [b for b in band_blocks if b.x0 >= split_x]
            
            left_col.sort(key=lambda b: (b.y0, b.x0))
            right_col.sort(key=lambda b: (b.y0, b.x0))
            
            ordered_blocks.extend(left_col)
            ordered_blocks.extend(right_col)
            
        # 3. Footers (at the very bottom of the page sequence)
        footers = [b for b in page.blocks if b.y0 >= footer_y]
        footers.sort(key=lambda b: (b.y0, b.x0))
        ordered_blocks.extend(footers)
        
    return ordered_blocks
