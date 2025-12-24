"""
One-time PDF to text extraction.
Run once: python -m src.extract
"""
import fitz  # PyMuPDF
from pathlib import Path
import json

DATA_DIR = Path(__file__).parent.parent / "data"
PDF_PATH = DATA_DIR / "title26.pdf"
TEXT_PATH = DATA_DIR / "title26.txt"
PAGES_PATH = DATA_DIR / "title26_pages.json"


def extract_pdf_to_text():
    """Extract all text from PDF and save to files."""
    
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
    
    print(f"📄 Opening {PDF_PATH}...")
    doc = fitz.open(PDF_PATH)
    print(f"   Total pages: {len(doc)}")
    
    all_text = []
    pages_data = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        if text.strip():
            all_text.append(f"\n\n--- PAGE {page_num + 1} ---\n\n{text}")
            pages_data.append({
                "page": page_num + 1,
                "text": text,
                "char_count": len(text)
            })
        
        if (page_num + 1) % 500 == 0:
            print(f"   Processed {page_num + 1} pages...")
    
    doc.close()
    
    # Save full text
    full_text = "".join(all_text)
    TEXT_PATH.write_text(full_text, encoding="utf-8")
    print(f"✓ Saved full text to {TEXT_PATH}")
    print(f"   Total characters: {len(full_text):,}")
    
    # Save pages as JSON for structured access
    with open(PAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(pages_data, f, indent=2)
    print(f"✓ Saved {len(pages_data)} pages to {PAGES_PATH}")
    
    return TEXT_PATH, PAGES_PATH


if __name__ == "__main__":
    extract_pdf_to_text()

