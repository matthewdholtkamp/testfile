import scripts.run_pipeline as rp

# Manually test extract_pdf_text with an open access PDF
# I will use a known open access PDF DOI to test Tier C.
doi = "10.1371/journal.pone.0284483" # Random PLOS one article
html, pdf_url = rp.resolve_doi_and_find_pdf(doi)
print(f"PDF URL: {pdf_url}")

if pdf_url:
    text = rp.extract_pdf_text(pdf_url)
    if text:
        print("Successfully extracted PDF text. Length:", len(text))
        print(text[:500])
    else:
        print("Failed to extract PDF text.")
