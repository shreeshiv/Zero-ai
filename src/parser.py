"""
Parse Title 26 PDF and extract text chunks for indexing.
"""
import re
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator


@dataclass
class TaxChunk:
    """A chunk of tax code text with metadata."""
    text: str
    page_number: int
    section: str | None = None
    subtitle: str | None = None
    chapter: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "page_number": self.page_number,
            "section": self.section,
            "subtitle": self.subtitle,
            "chapter": self.chapter,
        }


# Patterns to extract structure
SECTION_PATTERN = re.compile(r"§\s*(\d+[A-Za-z]?(?:\.\d+)?)")
SUBTITLE_PATTERN = re.compile(r"Subtitle\s+([A-Z])[—\-–]\s*(.+?)(?:\n|$)", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r"CHAPTER\s+(\d+)[—\-–]\s*(.+?)(?:\n|$)", re.IGNORECASE)


def extract_text_from_pdf(pdf_path: Path) -> Iterator[tuple[int, str]]:
    """Extract text from each page of the PDF."""
    doc = fitz.open(pdf_path)
    print(f"📄 Processing {len(doc)} pages...")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            yield page_num + 1, text  # 1-indexed pages
    
    doc.close()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break first
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + chunk_size // 2:
                end = para_break
            else:
                # Look for sentence break
                sentence_break = text.rfind(". ", start, end)
                if sentence_break > start + chunk_size // 2:
                    end = sentence_break + 1
        
        chunks.append(text[start:end].strip())
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def parse_tax_code(pdf_path: Path, chunk_size: int = 1000) -> list[TaxChunk]:
    """Parse the tax code PDF into searchable chunks."""
    all_chunks = []
    
    current_subtitle = None
    current_chapter = None
    
    for page_num, page_text in extract_text_from_pdf(pdf_path):
        # Try to extract structure markers
        subtitle_match = SUBTITLE_PATTERN.search(page_text)
        if subtitle_match:
            current_subtitle = f"Subtitle {subtitle_match.group(1)}: {subtitle_match.group(2).strip()}"
        
        chapter_match = CHAPTER_PATTERN.search(page_text)
        if chapter_match:
            current_chapter = f"Chapter {chapter_match.group(1)}: {chapter_match.group(2).strip()}"
        
        # Chunk the page text
        chunks = chunk_text(page_text, chunk_size=chunk_size)
        
        for chunk_text_content in chunks:
            if len(chunk_text_content.strip()) < 50:  # Skip tiny chunks
                continue
            
            # Try to find section reference in chunk
            section_match = SECTION_PATTERN.search(chunk_text_content)
            section = f"§{section_match.group(1)}" if section_match else None
            
            all_chunks.append(TaxChunk(
                text=chunk_text_content,
                page_number=page_num,
                section=section,
                subtitle=current_subtitle,
                chapter=current_chapter,
            ))
    
    print(f"✓ Extracted {len(all_chunks)} chunks from tax code")
    return all_chunks


if __name__ == "__main__":
    from downloader import download_tax_code
    
    pdf_path = download_tax_code()
    chunks = parse_tax_code(pdf_path)
    
    # Show sample
    print("\n--- Sample Chunk ---")
    print(chunks[100].to_dict())

