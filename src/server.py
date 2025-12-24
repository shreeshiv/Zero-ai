"""
MCP Server for Tax Code Search.

This server provides semantic search over Title 26 (Internal Revenue Code).
"""
from mcp.server.fastmcp import FastMCP

from .indexer import get_index


# Create the MCP server
mcp = FastMCP(
    name="tax-code-search",
    instructions="""
    This server provides semantic search over the US Tax Code (Title 26 - Internal Revenue Code).
    
    Use the search_tax_code tool to find relevant sections of tax law based on natural language queries.
    The search uses semantic similarity to find the most relevant passages.
    
    Example queries:
    - "SALT deduction limit"
    - "standard deduction for seniors"
    - "capital gains tax rates"
    - "401k contribution limits"
    """,
)


@mcp.tool()
def search_tax_code(query: str, k: int = 5) -> list[dict]:
    """
    Search the US Tax Code (Title 26) for relevant passages.
    
    Args:
        query: Natural language query describing what you're looking for.
               Examples: "SALT deduction limit", "capital gains tax", "401k contribution"
        k: Number of results to return (default: 5, max: 20)
    
    Returns:
        List of matching passages with:
        - text: The relevant text from the tax code
        - page_number: Page in the official PDF
        - section: Tax code section (e.g., "§164")
        - subtitle: Tax code subtitle (e.g., "Subtitle A: Income Taxes")
        - chapter: Tax code chapter
        - score: Relevance score (higher is better)
    """
    # Clamp k to reasonable range
    k = max(1, min(k, 20))
    
    index = get_index()
    results = index.search(query, k=k)
    
    return results


@mcp.tool()
def get_tax_code_section(page_number: int) -> dict:
    """
    Get the full text of a specific page from the tax code.
    
    Args:
        page_number: The page number to retrieve
        
    Returns:
        Dictionary with page content and any chunks from that page
    """
    index = get_index()
    
    # Find all chunks from this page
    page_chunks = [
        chunk.to_dict() 
        for chunk in index.chunks 
        if chunk.page_number == page_number
    ]
    
    if not page_chunks:
        return {"error": f"No content found for page {page_number}"}
    
    return {
        "page_number": page_number,
        "chunks": page_chunks,
        "total_chunks": len(page_chunks),
    }


@mcp.tool()
def get_index_stats() -> dict:
    """
    Get statistics about the tax code index.
    
    Returns:
        Dictionary with index statistics
    """
    index = get_index()
    
    if not index._loaded:
        return {"status": "not_loaded", "message": "Index will be built on first search"}
    
    # Collect stats
    sections = set()
    subtitles = set()
    chapters = set()
    pages = set()
    
    for chunk in index.chunks:
        pages.add(chunk.page_number)
        if chunk.section:
            sections.add(chunk.section)
        if chunk.subtitle:
            subtitles.add(chunk.subtitle)
        if chunk.chapter:
            chapters.add(chunk.chapter)
    
    return {
        "status": "loaded",
        "total_chunks": len(index.chunks),
        "total_pages": len(pages),
        "unique_sections": len(sections),
        "unique_subtitles": len(subtitles),
        "unique_chapters": len(chapters),
        "page_range": [min(pages), max(pages)] if pages else None,
    }


def main():
    """Run the MCP server."""
    # Pre-build the index on startup
    print("🚀 Starting Tax Code Search MCP Server...")
    index = get_index()
    index.build()
    
    # Start the server
    mcp.run()


if __name__ == "__main__":
    main()

