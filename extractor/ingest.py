import fitz
from extractor.models import TextBlock, PageBlocks, ExtractionContext

def ingest_pdf(pdf_path: str, slug: str) -> ExtractionContext:
    """
    Stage 1: Open PDF with PyMuPDF and extract raw text blocks.
    Preserves exact font names, sizes, flags, and physical coordinates.
    """
    doc = fitz.open(pdf_path)
    context = ExtractionContext(pdf_path=pdf_path, slug=slug)
    
    for page_num, page in enumerate(doc):
        page_dict = page.get_text("dict")
        width = page_dict["width"]
        height = page_dict["height"]
        
        blocks = []
        for b in page_dict.get("blocks", []):
            if b.get("type") != 0:  # Only text blocks (type 0)
                continue
                
            x0, y0, x1, y1 = b["bbox"]
            
            # 1. Reconstruct block text and gather font statistics
            font_counts = {}
            block_lines = []
            
            for line in b.get("lines", []):
                line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                if line_text:
                    block_lines.append(line_text)
                    
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                        
                    font_key = (span.get("font", "Unknown"), span.get("size", 10.0), span.get("flags", 0))
                    char_count = len(text)
                    font_counts[font_key] = font_counts.get(font_key, 0) + char_count
            
            block_text = "\n".join(block_lines).strip()
            
            if not block_text:
                continue
                
            # 2. Determine dominant font (font with most characters in this block)
            if font_counts:
                dominant_font_key = max(font_counts.items(), key=lambda x: x[1])[0]
                dominant_font, dominant_size, dominant_flags = dominant_font_key
            else:
                dominant_font, dominant_size, dominant_flags = "Unknown", 10.0, 0
                
            tb = TextBlock(
                text=block_text,
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                font=dominant_font,
                size=dominant_size,
                flags=dominant_flags,
                page_num=page_num,
                block_num=b.get("number", -1)
            )
            blocks.append(tb)
            
        pb = PageBlocks(
            page_num=page_num,
            width=width,
            height=height,
            blocks=blocks
        )
        context.pages.append(pb)
        
    doc.close()
    return context
