import re
from typing import List
from extractor.models import SemanticType, SemanticBlock, TextBlock, DocumentCorpus, ExtractionContext

class State:
    PREAMBLE = 1
    AUTHOR_ZONE = 2
    AFFILIATION_ZONE = 3
    ABSTRACT_ZONE = 4
    KEYWORD_ZONE = 5
    BODY = 6

def is_bold(font_name: str) -> bool:
    name = font_name.lower()
    return "bold" in name or "heavy" in name or "medi" in name or "black" in name

def classify_preamble(ordered_blocks: List[TextBlock], corpus: DocumentCorpus, context: ExtractionContext) -> List[SemanticBlock]:
    state = State.PREAMBLE
    results = []
    
    found_title = False
    title_y_max = 0.0
    author_y_max = 0.0
    last_title_text = ""
    abstract_blocks = 0
    
    for block in ordered_blocks:
        if state == State.BODY:
            break
            
        text = block.text.strip()
        text_lower = text.lower()
        size = block.size
        y0 = block.y0
        page_num = block.page_num
        
        sem_type = SemanticType.FRONT_MATTER
        conf = 0.0
        reason = "Unknown preamble material"
        
        # 1. UNIVERSAL TITLE DETECTION (Page 0)
        # Allows finding TITLE even if we prematurely entered AUTHOR_ZONE (e.g. magazine layouts)
        is_title = False
        title_conf = 0.0
        title_reasons = []
        
        if page_num == 0:
            if size >= corpus.title_font_size * 0.95:
                title_conf += 0.90
                title_reasons.append("matches corpus title_font_size")
            elif size >= corpus.title_font_size * 0.85 and y0 < 0.40:
                title_conf += 0.60
                title_reasons.append("large font at top of page 0")
                if block.spans_columns or (block.x1 - block.x0 > 0.40):
                    title_conf += 0.30
                    title_reasons.append("spans columns")
                    
            if title_conf >= 0.85:
                is_title = True
                
            word_count = len(text.split())
            has_punctuation = bool(re.search(r'[:\-]', text))
            is_title_exception = text_lower in ["bert", "gpt-3", "t5"]
            is_publisher_metadata = bool(re.search(r'\b(doi|queue\.acm\.org|volume|proceedings|copyright)\b', text_lower)) or text_lower.startswith('http')
            is_numeric = bool(re.match(r'^\d+$', text)) and len(text) < 5
            
            if is_title:
                if word_count < 2 and not is_title_exception and not has_punctuation:
                    is_title = False
                elif size <= corpus.body_font_size * 1.05:
                    is_title = False
                elif is_publisher_metadata or is_numeric:
                    is_title = False
                
            # If we already found a title block, merge subsequent large blocks safely
            if not is_title and found_title:
                if size >= corpus.title_font_size * 0.90 and y0 - title_y_max < 0.05:
                    if not last_title_text.endswith(('.', '?', '!')):
                        is_title = True
                        title_conf = 0.85
                        title_reasons.append("adjacent large block")
            
            # Reject if it strongly looks like AUTHORS
            if is_title and size < corpus.title_font_size * 0.90 and len(re.findall(r'[A-Z][a-z]+', text)) >= 2 and len(text.split()) > 2:
                is_title = False
                
        if is_title:
            sem_type = SemanticType.TITLE
            conf = min(1.0, title_conf)
            reason = ", ".join(title_reasons)
            found_title = True
            title_y_max = max(title_y_max, block.y1)
            last_title_text = text
            state = State.PREAMBLE  # Ensure we process authors next
            
        elif state == State.PREAMBLE:
            # If not a title and we are in PREAMBLE
            if found_title:
                state = State.AUTHOR_ZONE
            elif page_num == 0 and y0 > 0.40:
                state = State.AUTHOR_ZONE
            elif page_num == 0 and text.startswith("BY ") and len(re.findall(r'[A-Z]{3,}', text)) >= 2:
                sem_type = SemanticType.AUTHORS
                conf = 0.90
                reason = "Explicit BY author line before title"
                author_y_max = max(author_y_max, block.y1)

        # 2. AUTHOR_ZONE STATE
        if state == State.AUTHOR_ZONE and sem_type == SemanticType.FRONT_MATTER:
            author_conf = 0.0
            reasons = []
            
            word_count = len(text.split())
            has_institution = bool(re.search(r'\b(university|institute|inc|corp|lab|research)\b', text_lower)) or "@" in text
            is_prose = bool(re.search(r'\b(is|are|we|our|this|paper|presents|propose|can|use|focus)\b', text_lower))
            if text.endswith('.') and not text_lower.endswith(('inc.', 'corp.', 'ltd.', 'al.', 'univ.', 'dept.', 'u.s.a.')):
                is_prose = True
            
            # Abstract triggers the transition
            if text_lower.startswith("abstract") or text_lower.startswith("a b s t r a c t"):
                state = State.ABSTRACT_ZONE
            elif word_count >= 40 and is_prose and size <= corpus.body_font_size * 1.05:
                state = State.ABSTRACT_ZONE
            else:
                is_publisher_metadata = bool(re.search(r'\b(doi|queue\.acm\.org|volume|proceedings|copyright)\b', text_lower)) or text_lower.startswith('http')
                is_numeric = bool(re.match(r'^\d+$', text)) and len(text) < 5
                
                if is_publisher_metadata or is_numeric:
                    author_conf = 0.0
                elif word_count > 100:
                    author_conf = 0.0
                elif word_count > 20 and not has_institution:
                    comma_density = text.count(',') / word_count
                    has_sentence_punct = bool(re.search(r'[.!?]', text))
                    if comma_density > 0.15 and not has_sentence_punct and not is_prose:
                        pass # allow it as a list-like structure
                    else:
                        author_conf = 0.0
                elif is_prose:
                    # Rule 16: Prose-like sentences (verbs, punctuation)
                    author_conf = 0.0
                else:
                    if page_num == 0 and found_title and y0 - title_y_max < 0.25:
                        author_conf += 0.40
                        reasons.append("follows TITLE")
                    if size < corpus.title_font_size * 0.85:
                        author_conf += 0.20
                        reasons.append("size < title_size * 0.85")
                    if len(re.findall(r'[A-Z][a-z]+', text)) >= 2:
                        author_conf += 0.30
                        reasons.append("title-case names")
                    if len(re.findall(r'[A-Z]{3,}', text)) >= 2:
                        author_conf += 0.30
                        reasons.append("all-caps names")
                    if has_institution:
                        author_conf += 0.30
                        reasons.append("has institution")
                    if not any(k in text_lower for k in ["abstract", "http", ":", "keywords", "categories"]):
                        author_conf += 0.10
                        reasons.append("no invalid tokens")
                    
                if author_conf >= 0.70:
                    sem_type = SemanticType.AUTHORS
                    conf = min(1.0, author_conf)
                    reason = ", ".join(reasons)
                    author_y_max = max(author_y_max, block.y1)
                else:
                    if page_num > 0 or (author_y_max > 0 and y0 - author_y_max > 0.15) or has_institution:
                        state = State.AFFILIATION_ZONE

        # 3. AFFILIATION_ZONE STATE
        if state == State.AFFILIATION_ZONE and sem_type == SemanticType.FRONT_MATTER:
            aff_conf = 0.0
            reasons = []
            
            if text_lower.startswith("abstract") or text_lower.startswith("a b s t r a c t"):
                state = State.ABSTRACT_ZONE
            elif word_count >= 40 and is_prose and size <= corpus.body_font_size * 1.05:
                state = State.ABSTRACT_ZONE
            else:
                if page_num == 0 and author_y_max > 0 and y0 - author_y_max < 0.15:
                    aff_conf += 0.30
                    reasons.append("follows AUTHORS")
                if "@" in text:
                    aff_conf += 0.40
                    reasons.append("contains @")
                if re.search(r'\b(university|institute|research|lab|inc|corp|department|school)\b', text_lower):
                    aff_conf += 0.40
                    reasons.append("contains institution keywords")
                if size <= corpus.body_font_size * 1.15:
                    aff_conf += 0.10
                    reasons.append("size <= body_size * 1.15")
                    
                if aff_conf >= 0.50:
                    sem_type = SemanticType.AFFILIATIONS
                    conf = min(1.0, aff_conf)
                    reason = ", ".join(reasons)
                
        # 4. ABSTRACT_ZONE STATE
        if state == State.ABSTRACT_ZONE and sem_type == SemanticType.FRONT_MATTER:
            abstract_blocks += 1
            if abstract_blocks > len(ordered_blocks) * 0.20:
                state = State.BODY
                break
                
            is_publisher_metadata = bool(re.search(r'\b(doi|queue\.acm\.org|volume|proceedings|copyright)\b', text_lower)) or text_lower.startswith('http')
            is_numeric = bool(re.match(r'^\d+$', text)) and len(text) < 5
            
            if is_numeric or is_publisher_metadata:
                sem_type = SemanticType.FRONT_MATTER
                conf = 0.90
                reason = "numeric or metadata block"
            elif any(text_lower.startswith(k) for k in ["keywords", "key words", "index terms"]):
                state = State.KEYWORD_ZONE
            elif re.match(r'^(\d+|[IVX]+)[\.\s]', text) and (is_bold(block.font) or size > corpus.body_font_size * 1.02):
                state = State.BODY
                break
            elif re.match(r'^(introduction|1 introduction|1. introduction)$', text_lower):
                state = State.BODY
                break
            elif any(text_lower.startswith(k) for k in ["categories and subject descriptors", "general terms", "acm reference format"]):
                state = State.KEYWORD_ZONE
            else:
                sem_type = SemanticType.ABSTRACT
                conf = 0.90
                reason = "Block is inside ABSTRACT_ZONE"
                
        # 5. KEYWORD_ZONE STATE
        if state == State.KEYWORD_ZONE and sem_type == SemanticType.FRONT_MATTER:
            if any(text_lower.startswith(k) for k in ["keywords", "key words", "index terms", "categories and subject", "general terms", "additional key words", "acm reference format"]):
                sem_type = SemanticType.KEYWORDS
                conf = 0.90
                reason = "Explicit keyword/metadata prefix"
            elif re.match(r'^(\d+|[IVX]+)[\.\s]', text) and (is_bold(block.font) or size > corpus.body_font_size * 1.02):
                state = State.BODY
                break
            elif re.match(r'^(introduction|1 introduction|1. introduction)$', text_lower):
                state = State.BODY
                break
                
        # Escape hatch: if it's still FRONT_MATTER but clearly a section header, enter BODY
        if sem_type == SemanticType.FRONT_MATTER:
            if re.match(r'^(\d+|[IVX]+)[\.\s]', text) and (is_bold(block.font) or size > corpus.body_font_size * 1.02):
                state = State.BODY
                break
            if re.match(r'^(introduction|1 introduction|1. introduction)$', text_lower):
                state = State.BODY
                break
                
        results.append(SemanticBlock(
            source_block=block,
            semantic_type=sem_type,
            confidence=conf,
            reason=reason
        ))
        
    return results
