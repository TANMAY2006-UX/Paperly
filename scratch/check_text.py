from extractor.ingest import ingest_pdf
context = ingest_pdf("papers_pdf/Spanner.pdf", "spanner")
print("Spanner Block 3 Full Text:")
print(context.pages[1].blocks[3].text)
