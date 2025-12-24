"""
Chunk the extracted text into semantic pieces for embedding.
Chunks span across pages for better context.
"""
import re
import json
from pathlib import Path
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent.parent / "data"
PAGES_PATH = DATA_DIR / "title26_pages.json"
CHUNKS_PATH = DATA_DIR / "chunks.json"

# Config
CHUNK_SIZE = 4000
OVERLAP = 200


@dataclass
class TaxChunk:
    """A chunk of tax code text with metadata."""
    id: str
    text: str
    start_page: int
    end_page: int
    section: str | None = None
    
    def to_dict(self) -> dict:
        return asdict(self)


# Regex patterns
SECTION_PATTERN = re.compile(r'§\s*(\d+[A-Za-z]?(?:\.\d+)?)')
SEC_HEADER_PATTERN = re.compile(r'SEC\.\s*(\d+[A-Za-z]?)\.\s*([A-Z][A-Z\s,\-]+?)\.?\n', re.MULTILINE)


def find_section(text: str) -> str | None:
    """Extract section number from text."""
    match = SEC_HEADER_PATTERN.search(text)
    if match:
        return f"§{match.group(1)}"
    
    match = SECTION_PATTERN.search(text)
    if match:
        return f"§{match.group(1)}"
    
    return None


def create_chunks(chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[TaxChunk]:
    """Combine all pages and create chunks that span across pages."""
    
    if not PAGES_PATH.exists():
        raise FileNotFoundError(f"Run extract.py first: {PAGES_PATH}")
    
    with open(PAGES_PATH, "r", encoding="utf-8") as f:
        pages = json.load(f)
    
    print(f"📄 Combining {len(pages)} pages...")
    
    # Build combined text with page markers
    # Format: text with embedded markers like <PAGE:123>
    combined_text = ""
    page_positions = []  # List of (position, page_number)
    
    for page_data in pages:
        page_num = page_data["page"]
        page_text = page_data["text"]
        
        if page_text.strip():
            page_positions.append((len(combined_text), page_num))
            combined_text += page_text + "\n"
    
    print(f"   Combined text: {len(combined_text):,} characters")
    
    # Now chunk the combined text
    all_chunks = []
    chunk_id = 0
    start = 0
    
    while start < len(combined_text):
        end = min(start + chunk_size, len(combined_text))
        
        # Try to break at paragraph or sentence boundary
        if end < len(combined_text):
            para_break = combined_text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break
            else:
                sentence_break = combined_text.rfind(". ", start + chunk_size // 2, end)
                if sentence_break > start:
                    end = sentence_break + 1
        
        chunk_text = combined_text[start:end].strip()
        
        if len(chunk_text) >= 100:  # Skip tiny chunks
            # Find which pages this chunk spans
            start_page = 1
            end_page = 1
            
            for pos, page_num in page_positions:
                if pos <= start:
                    start_page = page_num
                if pos <= end:
                    end_page = page_num
            
            # Find section in chunk
            section = find_section(chunk_text)
            
            all_chunks.append(TaxChunk(
                id=f"chunk_{chunk_id}",
                text=chunk_text,
                start_page=start_page,
                end_page=end_page,
                section=section,
            ))
            chunk_id += 1
        
        # Move forward with overlap
        start = end - overlap if end < len(combined_text) else len(combined_text)
    
    print(f"✓ Created {len(all_chunks)} chunks")
    
    # Save chunks
    chunks_data = [c.to_dict() for c in all_chunks]
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=2)
    print(f"✓ Saved to {CHUNKS_PATH}")
    
    # Stats
    sections = set(c.section for c in all_chunks if c.section)
    avg_size = sum(len(c.text) for c in all_chunks) / len(all_chunks) if all_chunks else 0
    print(f"   Unique sections: {len(sections)}")
    print(f"   Avg chunk size: {avg_size:.0f} chars")
    
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
        print(f"\n[{c.id}] Pages {c.start_page}-{c.end_page} | {c.section}")
        print(f"Length: {len(c.text)} chars")
        print(c.text[:300] + "...")
