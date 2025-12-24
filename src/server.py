"""
MCP Server for Tax Code Search.
Gemini embeddings + Chroma Cloud.
"""
from mcp.server.fastmcp import FastMCP
from .indexer import get_index


mcp = FastMCP(
    name="tax-code-search",
    instructions="""
    Search the US Tax Code (Title 26 - Internal Revenue Code).
    Use search_tax_code to find relevant sections based on natural language queries.
    
    Examples:
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
        query: Natural language query (e.g., "SALT deduction limit", "senior citizen deduction")
        k: Number of results to return (default: 5, max: 20)
    
    Returns:
        List of matching passages with text, page numbers, section, and relevance score
    """
    k = max(1, min(k, 20))
    index = get_index()
    return index.search(query, k=k)


@mcp.tool()
def get_index_stats() -> dict:
    """Get statistics about the tax code index."""
    index = get_index()
    return index.stats()


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
