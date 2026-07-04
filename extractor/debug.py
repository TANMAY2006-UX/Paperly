import os
import fitz
from extractor.models import ExtractionContext, DocumentLayoutKind, BlockType

def draw_debug_overlays(context: ExtractionContext, output_dir: str = "debug_output") -> ExtractionContext:
    """
    Stage 5: Debug Rendering
    Generates a debug PDF with visual overlays to validate geometric algorithms.
    """
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{context.slug}_debug.pdf")
    
    doc = fitz.open(context.pdf_path)
    
    for p in context.pages:
        page = doc[p.page_num]
        layout = p.layout
        
        # 1. Draw Text Blocks
        for b in p.blocks:
            x0 = b.x0 * p.width
            y0 = b.y0 * p.height
            x1 = b.x1 * p.width
            y1 = b.y1 * p.height
            rect = fitz.Rect(x0, y0, x1, y1)
            
            is_noise = b.block_type == BlockType.NOISE
            is_spanning = b.spans_columns
            
            color = (0.5, 0.5, 0.5)  
            
            if not is_noise:
                if is_spanning:
                    color = (0.5, 0, 0.5)  # Purple
                else:
                    split_x = context.document_layout.primary_split_x if (context.document_layout and context.document_layout.primary_split_x) else (layout.column_split_x if layout.column_split_x else 0.5)
                    if b.x0 < split_x:
                        color = (0, 0.8, 0)  # Green
                    else:
                        color = (0, 0, 0.8)  # Blue
                        
            page.draw_rect(rect, color=color, width=1.5)
            
        # 2. Draw Header/Footer Zones
        header_y = layout.header_zone_y * p.height
        footer_y = layout.footer_zone_y * p.height
        
        page.draw_line(fitz.Point(0, header_y), fitz.Point(p.width, header_y), color=(0.8, 0.8, 0), width=2)
        page.draw_line(fitz.Point(0, footer_y), fitz.Point(p.width, footer_y), color=(0.8, 0, 0), width=2)
        
        # 3. Draw Gutters
        if context.document_layout and context.document_layout.kind == DocumentLayoutKind.DOUBLE_COLUMN:
            global_split = context.document_layout.primary_split_x
            if global_split:
                gx = global_split * p.width
                page.draw_line(fitz.Point(gx, 0), fitz.Point(gx, p.height), color=(1, 0.5, 0), width=3)
                
        if layout.column_count == 2 and layout.column_split_x:
            split_x_px = layout.column_split_x * p.width
            page.draw_line(fitz.Point(split_x_px, 0), fitz.Point(split_x_px, p.height), color=(1, 0.5, 0), width=1.5, dashes="[5 5]")
            
        # 4. Annotate Page
        publisher_name = context.publisher.name if context.publisher else "Unknown"
        doc_kind = context.document_layout.kind.name if context.document_layout else "UNKNOWN"
        doc_conf = context.document_layout.confidence if context.document_layout else 0.0
        
        annotation_text = (
            f"Page: {p.page_num}\n"
            f"Publisher: {publisher_name}\n"
            f"Local Layout: {layout.column_count}-col (Conf: {layout.confidence:.2f})\n"
            f"Doc Layout: {doc_kind} (Conf: {doc_conf:.2f})\n"
            f"Blocks: {len(p.blocks)}"
        )
        
        text_rect = fitz.Rect(p.width - 200, 10, p.width - 10, 100)
        page.draw_rect(text_rect, color=(0,0,0), fill=(1,1,1), width=1)
        page.insert_textbox(text_rect, annotation_text, fontsize=12, color=(0,0,0), align=0)
        
    doc.save(out_path)
    doc.close()
    
    context.log(
        stage="debug",
        action="generate_debug_pdf",
        reason=f"Saved debug overlay to {out_path}",
        details={"output_path": out_path}
    )
    return context
