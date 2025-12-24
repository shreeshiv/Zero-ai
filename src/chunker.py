"""
Chunk the extracted text into semantic pieces for embedding.
"""
import re
import json
from pathlib import Path
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent.parent / "data"
PAGES_PATH = DATA_DIR / "title26_pages.json"
CHUNKS_PATH = DATA_DIR / "chunks.json"


@dataclass
class TaxChunk:
    """A chunk of tax code text with metadata."""
    id: str
    text: str
    page_number: int
    section: str | None = None
    
    def to_dict(self) -> dict:
        return asdict(self)


# Regex patterns
SECTION_PATTERN = re.compile(r'§\s*(\d+[A-Za-z]?(?:\.\d+)?)')
SEC_HEADER_PATTERN = re.compile(r'SEC\.\s*(\d+[A-Za-z]?)\.\s*([A-Z][A-Z\s,\-]+?)\.?\n', re.MULTILINE)


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks, breaking at sentence boundaries."""
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end < len(text):
            # Try to break at paragraph
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break
            else:
                # Try sentence break
                sentence_break = text.rfind(". ", start + chunk_size // 2, end)
                if sentence_break > start:
                    end = sentence_break + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def find_section(text: str) -> str | None:
    """Extract section number from text."""
    # Look for SEC. X. header first
    match = SEC_HEADER_PATTERN.search(text)
    if match:
        return f"§{match.group(1)}"
    
    # Fall back to § symbol
    match = SECTION_PATTERN.search(text)
    if match:
        return f"§{match.group(1)}"
    
    return None


def create_chunks(chunk_size: int = 1500, overlap: int = 200) -> list[TaxChunk]:
    """Load pages and create chunks."""
    
    if not PAGES_PATH.exists():
        raise FileNotFoundError(f"Run extract.py first: {PAGES_PATH}")
    
    with open(PAGES_PATH, "r", encoding="utf-8") as f:
        pages = json.load(f)
    
    print(f"📄 Processing {len(pages)} pages...")
    
    all_chunks = []
    chunk_id = 0
    current_section = None
    
    for page_data in pages:
        page_num = page_data["page"]
        page_text = page_data["text"]
        
        # Check for section header on this page
        section = find_section(page_text)
        if section:
            current_section = section
        
        # Chunk the page
        page_chunks = chunk_text(page_text, chunk_size=chunk_size, overlap=overlap)
        
        for chunk_text_content in page_chunks:
            if len(chunk_text_content) < 50:  # Skip tiny chunks
                continue
            
            # Try to find section in chunk itself
            chunk_section = find_section(chunk_text_content) or current_section
            
            all_chunks.append(TaxChunk(
                id=f"chunk_{chunk_id}",
                text=chunk_text_content,
                page_number=page_num,
                section=chunk_section,
            ))
            chunk_id += 1
    
    print(f"✓ Created {len(all_chunks)} chunks")
    
    # Save chunks
    chunks_data = [c.to_dict() for c in all_chunks]
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=2)
    print(f"✓ Saved to {CHUNKS_PATH}")
    
    # Stats
    sections = set(c.section for c in all_chunks if c.section)
    print(f"   Unique sections found: {len(sections)}")
    
    return all_chunks


def load_chunks() -> list[dict]:
    """Load chunks from JSON file."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Run chunker.py first: {CHUNKS_PATH}")
    
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    chunks = create_chunks()
    
    # Show sample
    print("\n--- Sample Chunks ---")
    for c in chunks[:3]:
        print(f"\n[{c.id}] Page {c.page_number} | {c.section}")
        print(c.text[:200] + "...")

