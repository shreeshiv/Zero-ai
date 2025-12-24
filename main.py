"""
REST API + MCP SSE Server for Tax Code Search.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount

load_dotenv()

# API Key auth
API_KEY = os.getenv("API_KEY", "zero-tax-api-key-2024")

# Lazy load indexer
_index = None

def get_tax_index():
    global _index
    if _index is None:
        from src.indexer import TaxCodeIndex
        _index = TaxCodeIndex()
    return _index


# ============== MCP Server ==============
mcp = FastMCP(
    name="tax-code-search",
    instructions="Search the US Tax Code (Title 26) using semantic search.",
)

@mcp.tool()
def search_tax_code(query: str, k: int = 5) -> list[dict]:
    """
    Search the US Tax Code for relevant passages.
    
    Args:
        query: Natural language query (e.g., "SALT deduction limit")
        k: Number of results (1-20)
    """
    k = max(1, min(k, 20))
    index = get_tax_index()
    return index.search(query, k=k)

@mcp.tool()
def get_index_stats() -> dict:
    """Get statistics about the tax code index."""
    index = get_tax_index()
    return index.stats()


# ============== FastAPI App ==============
app = FastAPI(
    title="Zero Tax Code Search API",
    description="REST API + MCP Server for US Tax Code search",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ============== REST Endpoints ==============
@app.get("/")
async def root():
    return {
        "name": "Zero Tax Code Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "mcp": "/mcp (SSE endpoint for MCP clients)",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, api_key: str = Depends(verify_api_key)):
    """Search the US Tax Code."""
    k = max(1, min(request.k, 20))
    try:
        index = get_tax_index()
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
    """GET version of search."""
    return await search(SearchRequest(query=q, k=k), api_key)


@app.get("/stats", response_model=StatsResponse)
async def stats(api_key: str = Depends(verify_api_key)):
    """Get index statistics."""
    try:
        index = get_tax_index()
        return index.stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== MCP SSE Endpoint ==============
sse_transport = SseServerTransport("/mcp/messages/")

@app.get("/mcp")
async def mcp_sse_endpoint(request: Request):
    """SSE endpoint for MCP clients."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp._mcp_server.run(
            streams[0], streams[1], mcp._mcp_server.create_initialization_options()
        )


@app.post("/mcp/messages/")
async def mcp_messages(request: Request):
    """Handle MCP messages."""
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
