from extractor.ingest import ingest_pdf

context = ingest_pdf("papers_pdf/Spanner.pdf", "spanner")
block_counts = [len(p.blocks) for p in context.pages]
print(f"Min blocks: {min(block_counts)}")
print(f"Max blocks: {max(block_counts)}")
print(f"Avg blocks: {sum(block_counts)/len(block_counts):.1f}")
for page_num in [0, 1, 2, 10, 20]:
    if page_num < len(block_counts):
        print(f"Page {page_num} blocks: {block_counts[page_num]}")

print("\nFirst five raw blocks of page 1:")
for i, b in enumerate(context.pages[1].blocks[:5]):
    text = b.text.replace("\n", " ")
    print(f"Block {i}: {text[:50]}... bbox=(x0={b.x0:.1f}, y0={b.y0:.1f}, x1={b.x1:.1f}, y1={b.y1:.1f})")
