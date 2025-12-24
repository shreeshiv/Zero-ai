# Zero-AI Tax Code Search

Semantic search over the US Tax Code (Title 26) using Gemini embeddings + Chroma Cloud.

## 🔗 Live API

```
https://zero-ai-production-03a0.up.railway.app
```

## Purpose

LLMs have knowledge cutoffs that miss recent tax law changes. This server provides real-time access to the latest tax code and general search query

## Quick Start

### Search the Tax Code

```bash
curl "https://zero-ai-production-03a0.up.railway.app/search?q=SALT+deduction+limit&k=3" \
  -H "Authorization: Bearer zero-tax-api-key-2024"
```

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

## API Endpoints

| Endpoint            | Method | Description        |
| ------------------- | ------ | ------------------ |
| `/health`           | GET    | Health check       |
| `/docs`             | GET    | Swagger UI         |
| `/search?q=...&k=5` | GET    | Search tax code    |
| `/search`           | POST   | Search (JSON body) |
| `/stats`            | GET    | Index statistics   |
| `/mcp`              | GET    | MCP SSE endpoint   |

## MCP Configuration (Cursor)

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tax-code": {
      "url": "https://zero-ai-production-03a0.up.railway.app/mcp"
    }
  }
}
```

Then ask Cursor: _"Search the tax code for SALT deduction limits"_

## Environment Variables

```
GEMINI_API_KEY=your-gemini-key
CHROMA_API_KEY=your-chroma-key
CHROMA_TENANT=your-tenant
CHROMA_DATABASE=your-database
```

## Tech Stack

- **Embeddings**: Google Gemini (`text-embedding-004`)
- **Vector DB**: Chroma Cloud
- **API**: FastAPI
- **Data**: Title 26 - Internal Revenue Code
