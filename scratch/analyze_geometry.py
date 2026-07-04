from extractor.ingest import ingest_pdf
from extractor.normalize import normalize_context

context = ingest_pdf("papers_pdf/Spanner.pdf", "spanner")
context = normalize_context(context)

print("--- Page 1 Block Geometry ---")
p1 = context.pages[1]
for i, b in enumerate(p1.blocks):
    width = b.x1 - b.x0
    is_filtered = len(b.text) <= 10 or width >= 0.8
    reason = []
    if len(b.text) <= 10:
        reason.append("text<=10")
    if width >= 0.8:
        reason.append("width>=0.8")
        
    print(f"Block {i:02d}: x0={b.x0:.4f}, x1={b.x1:.4f}, w={width:.4f}, len={len(b.text)}")
    print(f"         Filtered? {is_filtered} ({', '.join(reason) if reason else 'None'})")
    print(f"         Preview: {b.text[:40].replace(chr(10), ' ')}")

print("\n--- Histograms ---")
for page_num in [1, 2, 10, 20]:
    p = context.pages[page_num]
    x0s = [b.x0 for b in p.blocks if len(b.text) > 10 and (b.x1 - b.x0) < 0.8]
    left_cluster = [x for x in x0s if x < 0.45]
    right_cluster = [x for x in x0s if x >= 0.45]
    
    print(f"Page {page_num}:")
    print(f"  Raw blocks: {len(p.blocks)}")
    print(f"  Valid blocks: {len(x0s)}")
    if left_cluster:
        print(f"  Left cluster  (N={len(left_cluster)}): {', '.join([f'{x:.3f}' for x in left_cluster])}")
    if right_cluster:
        print(f"  Right cluster (N={len(right_cluster)}): {', '.join([f'{x:.3f}' for x in right_cluster])}")
