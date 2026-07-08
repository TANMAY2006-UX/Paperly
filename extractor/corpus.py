import re
from collections import Counter
from statistics import median
from typing import Set

from extractor.models import ExtractionContext, DocumentCorpus

def is_bold_font(font_name: str, flags: int = 0) -> bool:
    """
    Centralized helper to determine if a font is bold.
    Supports explicit PyMuPDF flags and multiple publisher naming conventions.
    """
    # PyMuPDF TEXT_FONT_BOLD flag is bit 4 (value 16)
    if flags & 16:
        return True
    
    font_lower = font_name.lower()
    
    # Common bold indicators in font names
    bold_indicators = ["bold", "-bd", "heavy", "black", "demi"]
    
    for indicator in bold_indicators:
        if indicator in font_lower:
            # Avoid matching words where 'bd' is part of a longer unrelated word, 
            # but usually font names are like 'Times-Bold' or 'NimbusRomNo9L-Medi'
            return True
            
    # Some ACM/IEEE fonts use 'Medi' (Medium/Demi-bold) as their bold weight for headings
    if "medi" in font_lower:
        return True

    return False

def compute_corpus(context: ExtractionContext) -> DocumentCorpus:
    """
    Computes document-wide stable statistical truths without modifying geometry.
    """
    body_font_sizes = []
    body_font_names = Counter()
    header_candidates = Counter()
    
    # Pass 1: Compute body statistics and collect running headers
    for page in context.pages:
        if not page.layout:
            continue
            
        header_y = page.layout.header_zone_y
        footer_y = page.layout.footer_zone_y
        
        for block in page.blocks:
            text = block.text.strip()
            if not text:
                continue
                
            # Running header detection
            if block.y0 <= header_y and block.y1 < 0.20:
                # Exclude obvious noise like pure digits
                if len(text) > 2 and not text.isdigit():
                    # Record the page number where this text appeared
                    header_candidates[(text, page.page_num)] += 1
            
            # Body text detection (Exclude page 0 entirely to avoid title/author size skewing)
            if page.page_num > 0:
                if block.y0 > header_y and block.y1 < footer_y:
                    # Ignore obvious noise or isolated characters
                    if len(text) > 10 and not text.isdigit():
                        body_font_sizes.append(block.size)
                        # Weight font names by length of text to find the truly dominant body font
                        body_font_names[block.font] += len(text)

    # Median is robust against outliers (like large headers or small footnotes)
    body_font_size = median(body_font_sizes) if body_font_sizes else 10.0
    body_font_name = body_font_names.most_common(1)[0][0] if body_font_names else "Unknown"
    
    # Check if bold is used frequently enough in the document to be a reliable signal
    bold_count = 0
    for page in context.pages:
        for block in page.blocks:
            if is_bold_font(block.font, block.flags):
                bold_count += 1
                
    is_bold_font_used = bold_count > 5
    
    # Process running headers (must appear on at least 3 distinct pages)
    header_page_counts = Counter()
    for (text, page_num) in header_candidates.keys():
        header_page_counts[text] += 1
        
    running_header_set = {text for text, count in header_page_counts.items() if count >= 3}
    
    # Pass 2: Compute title font size (Page 0 only)
    title_font_size = 0.0
    if context.pages:
        page0 = context.pages[0]
        header_y = page0.layout.header_zone_y if page0.layout else 0.0
        
        for block in page0.blocks:
            text = block.text.strip()
            # Must not be in header zone, must be substantial
            if block.y0 > header_y and len(text) > 3 and not text.isdigit():
                word_count = len(text.split())
                has_punctuation = bool(re.search(r'[:\-]', text))
                is_title_exception = text.lower() in ["bert", "gpt-3", "t5"]
                
                if word_count < 2 and not is_title_exception and not has_punctuation:
                    continue
                    
                if block.size > title_font_size:
                    title_font_size = block.size
                    
    # Safe fallback if page 0 was empty or lacked substantial blocks
    if title_font_size == 0.0:
        title_font_size = body_font_size * 1.5

    return DocumentCorpus(
        body_font_size=body_font_size,
        body_font_name=body_font_name,
        title_font_size=title_font_size,
        is_bold_font=is_bold_font_used,
        running_header_set=running_header_set
    )
