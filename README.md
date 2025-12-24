# Zero-AI Tax Code Search

An MCP (Model Context Protocol) server that enables semantic search over the US Tax Code (Title 26 - Internal Revenue Code).

## 🎯 Purpose

LLMs have knowledge cutoffs that miss recent tax law changes. This server provides real-time access to the latest tax code, including:
- 2025 SALT deduction changes
- Senior citizen deduction updates
- And all other provisions in Title 26

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Build the Index

The first run downloads the tax code (~50MB PDF) and builds a semantic search index:

```bash
python -c "from src.indexer import TaxCodeIndex; TaxCodeIndex().build()"
```

### 3. Run the MCP Server

```bash
python run_server.py
```

## 🔧 MCP Configuration

Add to your Claude/Cursor MCP config:

```json
{
  "mcpServers": {
    "tax-code-search": {
      "command": "python",
      "args": ["/path/to/Zero-ai/run_server.py"],
      "env": {}
    }
  }
}
```

Or using the installed script:

```json
{
  "mcpServers": {
    "tax-code-search": {
      "command": "tax-search-server",
      "env": {}
    }
  }
}
```

## 📚 Available Tools

### `search_tax_code`

Search the tax code using natural language.

**Parameters:**
- `query` (str): Natural language search query
- `k` (int): Number of results to return (default: 5, max: 20)

**Example:**
```
query: "SALT deduction limit"
k: 3
```

**Returns:** List of relevant passages with page numbers, section references, and relevance scores.

### `get_tax_code_section`

Retrieve all chunks from a specific page.

**Parameters:**
- `page_number` (int): Page number in the PDF

### `get_index_stats`

Get statistics about the indexed tax code.

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Tax Code PDF  │ ──▶ │   Parser     │ ──▶ │  Text Chunks    │
│  (Title 26)     │     │  (PyMuPDF)   │     │  with metadata  │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   MCP Server    │ ◀── │  FAISS Index │ ◀── │  Embeddings     │
│  (FastMCP)      │     │  (search)    │     │  (MiniLM)       │
└─────────────────┘     └──────────────┘     └─────────────────┘
```

## 📁 Project Structure

```
Zero-ai/
├── src/
│   ├── __init__.py
│   ├── downloader.py   # Downloads Title 26 PDF
│   ├── parser.py       # Extracts and chunks text
│   ├── indexer.py      # Builds semantic search index
│   └── server.py       # MCP server implementation
├── data/               # Downloaded PDF and index (gitignored)
├── run_server.py       # Entry point
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🔍 Example Searches

| Query | Finds |
|-------|-------|
| "SALT deduction limit" | State and local tax deduction limits (§164) |
| "standard deduction seniors" | Additional deduction for elderly/blind |
| "capital gains tax rates" | Long-term capital gains rates |
| "401k contribution limits" | Retirement contribution limits |
| "qualified business income deduction" | QBI/199A deduction rules |

## 📖 Data Source

Tax code is sourced from the official US House of Representatives:
- [Title 26 - Internal Revenue Code](https://uscode.house.gov/download/download.shtml)
- Updates automatically reflect congressional amendments

## License

MIT
