"""
Download Title 26 (Internal Revenue Code) from US House of Representatives.
"""
import httpx
import zipfile
import io
import re
import time
from pathlib import Path


# Title 26 - Internal Revenue Code ZIP URL (contains PDF)
DOWNLOAD_PAGE = "https://uscode.house.gov/download/download.shtml"
BASE_URL = "https://uscode.house.gov/download/"

DATA_DIR = Path(__file__).parent.parent / "data"


def get_with_retry(client: httpx.Client, url: str, max_retries: int = 3) -> httpx.Response:
    """Make GET request with retry logic."""
    for attempt in range(max_retries):
        try:
            response = client.get(url)
            response.raise_for_status()
            return response
        except (httpx.RemoteProtocolError, httpx.TimeoutException) as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"  ⚠ Connection issue, retrying in {wait_time}s... ({e})")
                time.sleep(wait_time)
            else:
                raise


def get_latest_title26_url() -> str:
    """Scrape the download page to find the latest Title 26 PDF zip URL."""
    print("🔍 Finding latest Title 26 download link...")
    
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = get_with_retry(client, DOWNLOAD_PAGE)
        
        # Find Title 26 PDF link (format: releasepoints/us/pl/XXX/XX/pdf_usc26@XXX-XX.zip)
        match = re.search(r'(releasepoints/[^"]+pdf_usc26[^"]+\.zip)', response.text)
        if not match:
            raise ValueError("Could not find Title 26 PDF download link")
        
        url = BASE_URL + match.group(1)
        print(f"✓ Found: {url}")
        return url


def download_tax_code(force: bool = False) -> Path:
    """Download the Title 26 PDF if not already present."""
    DATA_DIR.mkdir(exist_ok=True)
    pdf_path = DATA_DIR / "title26.pdf"
    
    if pdf_path.exists() and not force:
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if size_mb > 1:  # Valid PDF should be > 1MB
            print(f"✓ Tax code already downloaded: {pdf_path} ({size_mb:.1f} MB)")
            return pdf_path
    
    # Get latest URL
    zip_url = get_latest_title26_url()
    
    print(f"⬇ Downloading Title 26 from {zip_url}...")
    print("  (This may take a few minutes for ~50MB file)")
    
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        response = get_with_retry(client, zip_url)
        
        # Extract PDF from ZIP
        print("📦 Extracting PDF from ZIP...")
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            # Find the PDF file(s)
            pdf_files = [f for f in zf.namelist() if f.endswith('.pdf')]
            
            if not pdf_files:
                raise ValueError("No PDF found in ZIP file")
            
            # If multiple PDFs, concatenate them or use the main one
            if len(pdf_files) == 1:
                pdf_content = zf.read(pdf_files[0])
            else:
                # Multiple PDFs - save them all and we'll merge or use the largest
                print(f"  Found {len(pdf_files)} PDF files")
                largest_pdf = max(pdf_files, key=lambda f: zf.getinfo(f).file_size)
                print(f"  Using largest: {largest_pdf}")
                pdf_content = zf.read(largest_pdf)
        
        pdf_path.write_bytes(pdf_content)
        size_mb = len(pdf_content) / (1024 * 1024)
        print(f"✓ Downloaded {size_mb:.1f} MB to {pdf_path}")
    
    return pdf_path


if __name__ == "__main__":
    download_tax_code(force=True)
