from extractor.ingest import ingest_pdf
from extractor.normalize import normalize_context
from extractor.publishers import detect_publisher
from extractor.layout import detect_layout

context = ingest_pdf("papers_pdf/Spanner.pdf", "spanner")
context = normalize_context(context)
context = detect_publisher(context)
context = detect_layout(context)

print("\n--- Generating X-Coordinate Statistics ---")
for page_num in [1, 2, 10, 20]:
    p = context.pages[page_num]
    valid_blocks = [b for b in p.blocks if len(b.text) >= 10]
    
    print(f"\nPage {page_num}:")
    for i, b in enumerate(valid_blocks[:3]):  # Just show first few to verify
        print(f"  Block {i}: x0={b.x0:.3f}, x1={b.x1:.3f}, w={(b.x1 - b.x0):.3f} | {b.text[:30].replace(chr(10), ' ')}")
    
    x0s = [b.x0 for b in valid_blocks]
    left_c = [x for x in x0s if x < 0.45]
    right_c = [x for x in x0s if x >= 0.45]
    
    print(f"  Clusters: Left N={len(left_c)}, Right N={len(right_c)}")
    
    layout_log = next(log for log in reversed(context.audit_log) 
                      if log["action"] == "page_layout_detected" and log.get("page_num") == page_num)
    
    print(f"  Decision: {layout_log.get('column_count')}-column")
    print(f"  Confidence: {layout_log.get('confidence')}")
    if p.layout.column_split_x:
        print(f"  Potential Gutter: x={p.layout.column_split_x:.3f}")
    else:
        print(f"  Potential Gutter: None")
