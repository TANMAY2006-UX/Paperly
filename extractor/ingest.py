import fitz
from extractor.models import TextBlock, PageBlocks, ExtractionContext

def ingest_pdf(pdf_path: str, slug: str) -> ExtractionContext:
    """
    Stage 1: Open PDF with PyMuPDF and extract raw text blocks.
    Preserves exact font names, sizes, flags, and physical coordinates.

    MIGRATION NOTE (Phase 3D — Ingest Line-Level Migration):
    Now emits one TextBlock per PyMuPDF *Line* instead of per *Block*.
    This restores Typographic Assembly as the sole authority for paragraph
    reconstruction, removing PyMuPDF's opaque block-grouping heuristics from
    the structural pipeline.

    Rationale:
    - PyMuPDF's block-grouping silently merges section headings with the
      following paragraph body, bypassing the Phase B Hard Line Break gate.
    - A PyMuPDF Line is a deterministic, publisher-agnostic geometric unit.
    - Typographic Assembly was always designed to receive lines and reconstruct
      paragraphs. This restores its intended pre-condition.

    Contract:
    - block_num carries the originating PyMuPDF block number for provenance.
      Multiple lines from the same PyMuPDF block share the same block_num.
      This is correct and intentional. No downstream stage uses block_num as
      a unique line identifier.
    - Whitespace spans are included in text reconstruction to preserve
      intra-line spacing, but excluded from font-voting to prevent invisible
      layout characters from skewing typography detection.
    - Ligature resolution is NOT performed here; it remains in normalize.py.
    """
    doc = fitz.open(pdf_path)
    context = ExtractionContext(pdf_path=pdf_path, slug=slug)
    textblock_id_counter = 0

    for page_num, page in enumerate(doc):
        page_dict = page.get_text("dict")
        width = page_dict["width"]
        height = page_dict["height"]

        blocks = []
        for b in page_dict.get("blocks", []):
            if b.get("type") != 0:  # Only text blocks (type 0)
                continue

            block_num = b.get("number", -1)

            for line in b.get("lines", []):
                # 1. Reconstruct line text preserving intra-line whitespace.
                #    All spans are concatenated regardless of content, so that
                #    word spacing is preserved exactly as laid out by the PDF.
                line_text = "".join(span.get("text", "") for span in line.get("spans", []))

                if not line_text.strip():
                    # Skip lines that are purely whitespace — they carry no
                    # structural or typographic information.
                    continue

                # 2. Determine dominant font from non-whitespace spans only.
                #    Character-mass voting: the font/size/flags tuple with the
                #    most characters wins. Whitespace spans are excluded so that
                #    invisible layout spacing characters cannot skew typography.
                font_counts: dict = {}
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    font_key = (
                        span.get("font", "Unknown"),
                        span.get("size", 10.0),
                        span.get("flags", 0),
                    )
                    font_counts[font_key] = font_counts.get(font_key, 0) + len(text)

                if font_counts:
                    dominant_font_key = max(font_counts.items(), key=lambda x: x[1])[0]
                    dominant_font, dominant_size, dominant_flags = dominant_font_key
                else:
                    # Fallback: no non-whitespace spans (degenerate line)
                    dominant_font, dominant_size, dominant_flags = "Unknown", 10.0, 0

                # 3. Use the line's native bbox.
                #    PyMuPDF computes line["bbox"] as the geometric union of all
                #    spans within the line. We use it directly rather than
                #    re-computing a span union.
                lx0, ly0, lx1, ly1 = line["bbox"]

                tb = TextBlock(
                    text=line_text,
                    x0=lx0,
                    y0=ly0,
                    x1=lx1,
                    y1=ly1,
                    font=dominant_font,
                    size=dominant_size,
                    flags=dominant_flags,
                    page_num=page_num,
                    block_num=block_num,
                    textblock_id=textblock_id_counter,
                )
                blocks.append(tb)
                textblock_id_counter += 1

        pb = PageBlocks(
            page_num=page_num,
            width=width,
            height=height,
            blocks=blocks,
        )
        context.pages.append(pb)

    doc.close()
    return context
