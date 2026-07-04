import os
import json
from extractor.ingest import ingest_pdf
from extractor.normalize import normalize_context
from extractor.publishers import detect_publisher
from extractor.layout import detect_layout
from extractor.consensus import detect_consensus
from extractor.debug import draw_debug_overlays

papers = [
    "BERT.pdf",
    "Bbr Congestion Control.pdf",
    "In Search of an Understandable Consensus Algorithm.pdf",
    "Spanner.pdf"
]

results = []

for paper in papers:
    path = os.path.join("papers_pdf", paper)
    slug = os.path.splitext(paper)[0]
    
    print(f"Processing {paper}...")
    context = ingest_pdf(path, slug)
    context = normalize_context(context)
    context = detect_publisher(context)
    context = detect_layout(context)
    context = detect_consensus(context)
    draw_debug_overlays(context)
    # Get the header/footer zones assigned
    header_y = context.pages[0].layout.header_zone_y if context.pages else 0
    footer_y = context.pages[0].layout.footer_zone_y if context.pages else 1
    margin_log = next((log for log in context.audit_log if log["action"] == "dynamic_margins_detected"), None)
    
    results.append({
        "paper": paper,
        "header_zone_y": header_y,
        "footer_zone_y": footer_y,
        "margin_reason": margin_log["reason"] if margin_log else "No log"
    })

for res in results:
    print(f"--- {res['paper']} ---")
    print(f"Header: {res['header_zone_y']:.3f} | Footer: {res['footer_zone_y']:.3f} | {res['margin_reason']}")
