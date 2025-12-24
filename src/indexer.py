"""
Tax Code Search - Full Cloud Edition
Google Gemini (embeddings) + Chroma Cloud (vector DB)
"""
import os
import json
import time
import chromadb
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Config
GEMINI_MODEL = "models/text-embedding-004"
COLLECTION_NAME = "tax_code"
MAX_CHUNKS = 1000  # Limit for initial indexing

DATA_DIR = Path(__file__).parent.parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks.json"


def load_chunks(limit: int | None = None) -> list[dict]:
    """Load chunks from JSON file."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Chunks not found. Run:\n"
            f"  python -m src.extract\n"
            f"  python -m src.chunker"
        )
    
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    if limit:
        chunks = chunks[:limit]
    
    return chunks


class TaxCodeIndex:
    """Tax code search - Full Cloud with Gemini + Chroma Cloud."""
    
    def __init__(self):
        self.chroma_client: chromadb.CloudClient | None = None
        self.collection = None
        self._gemini_configured = False
    
    def _configure_gemini(self):
        """Configure Gemini API."""
        if not self._gemini_configured:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key or "your-" in api_key:
                raise ValueError("Set GEMINI_API_KEY in .env")
            genai.configure(api_key=api_key)
            self._gemini_configured = True
    
    def _get_chroma_client(self) -> chromadb.CloudClient:
        """Get Chroma Cloud client."""
        if self.chroma_client is None:
            api_key = os.getenv("CHROMA_API_KEY")
            tenant = os.getenv("CHROMA_TENANT")
            database = os.getenv("CHROMA_DATABASE")
            
            if not api_key or "your-" in api_key:
                raise ValueError("Set CHROMA_API_KEY in .env")
            if not tenant or "your-" in tenant:
                raise ValueError("Set CHROMA_TENANT in .env")
            if not database or "your-" in database:
                raise ValueError("Set CHROMA_DATABASE in .env")
            
            self.chroma_client = chromadb.CloudClient(
                tenant=tenant,
                database=database,
                api_key=api_key,
            )
        return self.chroma_client
    
    def _get_collection(self):
        """Get or create collection."""
        if self.collection is None:
            client = self._get_chroma_client()
            self.collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self.collection
    
    def _embed(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        """Get embeddings from Gemini."""
        self._configure_gemini()
        
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model=GEMINI_MODEL,
                content=text,
                task_type=task_type,
            )
            embeddings.append(result['embedding'])
        
        return embeddings
    
    def _embed_batch(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT", batch_size: int = 20) -> list[list[float]]:
        """Get embeddings in batches with rate limiting."""
        self._configure_gemini()
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for text in batch:
                result = genai.embed_content(
                    model=GEMINI_MODEL,
                    content=text,
                    task_type=task_type,
                )
                all_embeddings.append(result['embedding'])
            
            # Small delay to respect rate limits
            if i + batch_size < len(texts):
                time.sleep(0.1)
        
        return all_embeddings
    
    def build(self, force: bool = False, batch_size: int = 50, max_chunks: int = MAX_CHUNKS):
        """Build the search index in Chroma Cloud."""
        collection = self._get_collection()
        
        # Check if already has data
        if collection.count() > 0 and not force:
            print(f"✓ Index already exists with {collection.count()} chunks")
            return
        
        if force and collection.count() > 0:
            # Clear existing data
            ids = collection.get()["ids"]
            if ids:
                collection.delete(ids=ids)
            print("🗑 Cleared existing data")
        
        # Load chunks from JSON (limited)
        chunks = load_chunks(limit=max_chunks)
        
        print(f"🚀 Indexing {len(chunks)} chunks...")
        print(f"   Gemini: {GEMINI_MODEL}")
        print(f"   Chroma Cloud: ✓")
        
        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            texts = [c["text"] for c in batch]
            ids = [c["id"] for c in batch]
            metadatas = [{
                "page_number": c["page_number"],
                "section": c.get("section") or "",
            } for c in batch]
            
            # Get embeddings from Gemini
            embeddings = self._embed_batch(texts)
            
            # Add to Chroma Cloud
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            print(f"   Indexed {min(i + batch_size, len(chunks))}/{len(chunks)} chunks...")
        
        print(f"✓ Indexed {collection.count()} chunks to Chroma Cloud")
    
    def search(self, query: str, k: int = 5) -> list[dict]:
        """Search the tax code."""
        collection = self._get_collection()
        
        if collection.count() == 0:
            raise ValueError("Index is empty. Run: python -m src.indexer")
        
        # Get query embedding from Gemini
        self._configure_gemini()
        result = genai.embed_content(
            model=GEMINI_MODEL,
            content=query,
            task_type="RETRIEVAL_QUERY",
        )
        query_embedding = result['embedding']
        
        # Search Chroma Cloud
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
        
        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "text": results["documents"][0][i],
                "page_number": results["metadatas"][0][i]["page_number"],
                "section": results["metadatas"][0][i]["section"] or None,
                "score": 1 - results["distances"][0][i],
            })
        
        return output
    
    def stats(self) -> dict:
        """Get index stats."""
        collection = self._get_collection()
        return {
            "total_chunks": collection.count(),
            "collection_name": COLLECTION_NAME,
            "cloud": "Chroma Cloud",
            "embeddings": f"Google Gemini ({GEMINI_MODEL})",
        }


# Global instance
_index: TaxCodeIndex | None = None


def get_index() -> TaxCodeIndex:
    """Get or create the global index instance."""
    global _index
    if _index is None:
        _index = TaxCodeIndex()
    return _index


if __name__ == "__main__":
    index = TaxCodeIndex()
    index.build(force=True, max_chunks=1000)
    
    print("\n" + "="*60)
    print("Testing: 'SALT deduction limit'")
    print("="*60)
    for r in index.search("SALT deduction limit", k=3):
        print(f"\n[Page {r['page_number']}] {r['section']} (score: {r['score']:.3f})")
        print(r['text'][:200] + "...")
