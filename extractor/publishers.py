from typing import Optional
from extractor.models import PublisherProfile, ExtractionContext

ACM = PublisherProfile(
    name="ACM",
    expected_columns=2,
    has_mixed_layout=True,
    header_patterns=[
        "Permission to make digital or hard copies",
        "ACM ISBN",
        "ACM Reference Format",
        "http://dx.doi.org/10.",
        "Proceedings of the",
    ],
    section_numbering="numeric"
)

IEEE = PublisherProfile(
    name="IEEE",
    expected_columns=2,
    has_mixed_layout=True,
    header_patterns=[
        "IEEE",
        "Digital Object Identifier",
        "978-1-",
        "Authorized licensed use",
        "This article has been accepted",
    ],
    section_numbering="roman"
)

NEURIPS = PublisherProfile(
    name="NeurIPS",
    expected_columns=1,
    has_mixed_layout=False,
    header_patterns=[
        "Advances in Neural Information Processing Systems",
        "Neural Information Processing Systems Foundation",
        "arXiv:",
        "Preprint. Under review",
        "Equal contribution",
    ],
    section_numbering="numeric"
)

CVPR = PublisherProfile(
    name="CVPR",
    expected_columns=2,
    has_mixed_layout=True,
    header_patterns=[
        "IEEE Conference on Computer Vision",
        "978-1-",
        "CVPR",
    ],
    section_numbering="numeric"
)

CLASSICAL = PublisherProfile(
    name="Classical",
    expected_columns=2,
    has_mixed_layout=True,
    header_patterns=[
        "Communications of the ACM",
        "Bell System Technical Journal",
        "The Bell System",
    ],
    section_numbering="roman"
)

def detect_publisher(context: ExtractionContext) -> ExtractionContext:
    """
    Stage 3: Publisher Detection
    Analyzes visible text on early pages to match venue markers, copyright
    statements, or conference names. Never uses filename heuristics.
    """
    if not context.pages:
        return context
        
    # Analyze text from Page 0 (title/abstract page)
    first_page_text = "\n".join([b.text for b in context.pages[0].blocks]).lower()
    
    selected_publisher = NEURIPS  # Default fallback if unknown
    
    if any(p.lower() in first_page_text for p in [
        "advances in neural information processing",
        "neurips", "nips"
    ]):
        selected_publisher = NEURIPS
    elif any(p.lower() in first_page_text for p in [
        "ieee conference on computer vision",
        "cvpr", "iccv"
    ]):
        selected_publisher = CVPR
    elif "ieee" in first_page_text and any(p.lower() in first_page_text for p in [
        "ieee transactions", "proceedings of the ieee", "ieee/acm"
    ]):
        selected_publisher = IEEE
    elif any(p.lower() in first_page_text for p in [
        "acm", "association for computing machinery",
        "permission to make digital or hard copies"
    ]):
        selected_publisher = ACM
    elif context.pages[0].width > 700:  # Classical older papers are often wider (letter-wide)
        selected_publisher = CLASSICAL
        
    context.publisher = selected_publisher
    
    context.log(
        stage="publishers",
        action="detect_publisher",
        reason=f"Matched text patterns on page 0 to {selected_publisher.name}.",
        details={"detected": selected_publisher.name}
    )
    return context
