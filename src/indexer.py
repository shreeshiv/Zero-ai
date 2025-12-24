"""
Tax Code Search - Full Cloud Edition
Voyage AI (embeddings) + Chroma Cloud (vector DB)
"""
import os
import json
import chromadb
import voyageai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Config
VOYAGE_MODEL = "voyage-3-lite"
COLLECTION_NAME = "tax_code"

DATA_DIR = Path(__file__).parent.parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks.json"


def load_chunks() -> list[dict]:
    """Load chunks from JSON file."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Chunks not found. Run:\n"
            f"  python -m src.extract\n"
            f"  python -m src.chunker"
        )
    
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TaxCodeIndex:
    """Tax code search - Full Cloud with Voyage AI + Chroma Cloud."""
    
    def __init__(self):
        self.chroma_client: chromadb.CloudClient | None = None
        self.voyage_client: voyageai.Client | None = None
        self.collection = None
    
    def _get_voyage_client(self) -> voyageai.Client:
        """Get Voyage AI client."""
        if self.voyage_client is None:
            api_key = os.getenv("VOYAGE_API_KEY")
            if not api_key or "your-" in api_key:
                raise ValueError("Set VOYAGE_API_KEY in .env")
            self.voyage_client = voyageai.Client(api_key=api_key)
        return self.voyage_client
    
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
    
    def _embed(self, texts: list[str], input_type: str = "document") -> list[list[float]]:
        """Get embeddings from Voyage AI."""
        client = self._get_voyage_client()
        result = client.embed(texts, model=VOYAGE_MODEL, input_type=input_type)
        return result.embeddings
    
    def build(self, force: bool = False, batch_size: int = 100):
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
        
        # Load chunks from JSON
        chunks = load_chunks()
        
        print(f"🚀 Indexing {len(chunks)} chunks...")
        print(f"   Voyage AI: {VOYAGE_MODEL}")
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
            
            # Get embeddings from Voyage
            embeddings = self._embed(texts, input_type="document")
            
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
        
        # Get query embedding from Voyage
        query_embedding = self._embed([query], input_type="query")[0]
        
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
            "embeddings": f"Voyage AI ({VOYAGE_MODEL})",
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
    index.build(force=True)
    
    print("\n" + "="*60)
    print("Testing: 'SALT deduction limit'")
    print("="*60)
    for r in index.search("SALT deduction limit", k=3):
        print(f"\n[Page {r['page_number']}] {r['section']} (score: {r['score']:.3f})")
        print(r['text'][:200] + "...")
