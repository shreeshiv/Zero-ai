"""
REST API for Tax Code Search.
Deploy anywhere, call from anywhere.
"""
import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

load_dotenv()

# API Key auth
API_KEY = os.getenv("API_KEY", "zero-tax-api-key-2024")


app = FastAPI(
    title="Zero Tax Code Search API",
    description="Semantic search over US Tax Code (Title 26)",
    version="1.0.0",
)

# CORS for web apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Lazy load indexer
_index = None

def get_index():
    global _index
    if _index is None:
        from src.indexer import TaxCodeIndex
        _index = TaxCodeIndex()
    return _index


# Auth dependency
async def verify_api_key(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    key = authorization.replace("Bearer ", "").strip()
    
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return key


# Request/Response models
class SearchRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"query": "SALT deduction limit", "k": 5}
    })
    query: str
    k: int = 5


class SearchResult(BaseModel):
    text: str
    start_page: int
    end_page: int
    section: str | None
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    count: int


class StatsResponse(BaseModel):
    total_chunks: int
    collection_name: str
    cloud: str
    embeddings: str


# Endpoints
@app.get("/")
async def root():
    return {
        "name": "Zero Tax Code Search API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check - returns immediately without loading index."""
    return {"status": "healthy"}


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, api_key: str = Depends(verify_api_key)):
    """
    Search the US Tax Code (Title 26) for relevant passages.
    """
    k = max(1, min(request.k, 20))
    
    try:
        index = get_index()
        results = index.search(request.query, k=k)
        
        return SearchResponse(
            query=request.query,
            results=[SearchResult(**r) for r in results],
            count=len(results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_get(q: str, k: int = 5, api_key: str = Depends(verify_api_key)):
    """GET version of search for easy testing."""
    return await search(SearchRequest(query=q, k=k), api_key)


@app.get("/stats", response_model=StatsResponse)
async def stats(api_key: str = Depends(verify_api_key)):
    """Get index statistics."""
    try:
        index = get_index()
        return index.stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
