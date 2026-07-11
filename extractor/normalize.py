import re
import unicodedata
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

def remove_zero_width(text: str) -> str:
    """Removes zero-width and formatting control characters."""
    return re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', text)

def safe_nfkc(text: str) -> str:
    """
    Applies NFKC normalization, but strictly isolates it to specific safe ranges to 
    prevent corrupting Mathematical symbols, Superscripts, Greek letters, or Arrows.
    """
    def is_math_or_protected(ch: str) -> bool:
        cp = ord(ch)
        # Mathematical Operators (U+2200-U+22FF)
        if 0x2200 <= cp <= 0x22FF: return True
        # Greek and Coptic (U+0370-U+03FF)
        if 0x0370 <= cp <= 0x03FF: return True
        # Superscripts and Subscripts (U+2070-U+209F)
        if 0x2070 <= cp <= 0x209F: return True
        # Arrows (U+2190-U+21FF)
        if 0x2190 <= cp <= 0x21FF: return True
        # Supplemental Mathematical Operators (U+2A00-U+2AFF)
        if 0x2A00 <= cp <= 0x2AFF: return True
        # Miscellaneous Mathematical Symbols-A and B (U+27C0-U+29FF)
        if 0x27C0 <= cp <= 0x29FF: return True
        return False

    result = []
    for ch in text:
        if is_math_or_protected(ch):
            result.append(ch)
        else:
            result.append(unicodedata.normalize('NFKC', ch))
    return "".join(result)

def normalize_context(context: ExtractionContext) -> ExtractionContext:
    """
    Stage 2: Normalize coordinates, resolve ligatures, apply deterministic 
    de-hyphenation, and remove zero-width noise.
    """
    total_corrected = 0
    total_removed = 0
    
    # Pass 1: Build Document-Bounded Vocabulary for safe de-hyphenation
    vocab = set()
    for pb in context.pages:
        for b in pb.blocks:
            # We want purely alphabetical words (at least 3 characters is safe)
            for word in re.findall(r'\b[a-zA-Z]{3,}\b', b.text):
                vocab.add(word.lower())

    hyphen_pattern = re.compile(r'([a-zA-Z]+)-\n([a-zA-Z]+)')

    def dehyphenate(match):
        prefix = match.group(1)
        suffix = match.group(2)
        candidate = (prefix + suffix).lower()
        if candidate in vocab:
            return prefix + suffix
        return prefix + "-" + suffix

    # Pass 2: Normalization
    for pb in context.pages:
        normalized_blocks = []
        for b in pb.blocks:
            nx0 = b.x0 / pb.width
            ny0 = b.y0 / pb.height
            nx1 = b.x1 / pb.width
            ny1 = b.y1 / pb.height
            
            if nx0 >= nx1 or ny0 >= ny1:
                total_removed += 1
                continue
                
            old_text = b.text
            
            # 1. Soft Hyphens followed by newline (and soft hyphens generally)
            text = old_text.replace('\u00AD\n', '')
            text = text.replace('\u00AD', '')
            
            # 2. Document-Bounded De-hyphenation (Hard hyphen across newline)
            text = hyphen_pattern.sub(dehyphenate, text)
            
            # 3. Ligature resolution
            text = resolve_ligatures(text)
            
            # 4. Zero-width character removal
            text = remove_zero_width(text)
            
            # 5. Safe NFKC normalization
            text = safe_nfkc(text)
            
            if old_text != text:
                total_corrected += 1
                
            if not text.strip():
                total_removed += 1
                continue
                
            normalized_tb = TextBlock(
                text=text,
                x0=nx0,
                y0=ny0,
                x1=nx1,
                y1=ny1,
                font=b.font,
                size=b.size,
                flags=b.flags,
                page_num=b.page_num,
                block_num=b.block_num,
                textblock_id=b.textblock_id
            )
            normalized_blocks.append(normalized_tb)
            
        pb.blocks = normalized_blocks
        
    context.log(
        stage="normalize",
        action="normalize_coordinates_and_text",
        reason="Convert coordinates, resolve ligatures, apply safe NFKC, and resolve hyphens against local vocab.",
        details={"blocks_modified": total_corrected, "blocks_removed": total_removed}
    )
    return context
