import fitz
doc = fitz.open("papers_pdf/Deep Residual Learning for Image Recognition.pdf")
print("--- FIRST PAGE TEXT ---")
print(doc[0].get_text())
print("--- END FIRST PAGE TEXT ---")
doc.close()
