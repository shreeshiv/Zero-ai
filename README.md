# Zero-AI Tax Code Search

Semantic search over the US Tax Code (Title 26) using Gemini embeddings + Chroma Cloud.

## 🔗 Live API

```
https://zero-ai-production-03a0.up.railway.app
```

## Purpose

LLMs have knowledge cutoffs that miss recent tax law changes. This server provides real-time access to the latest tax code, including:

- 2025 SALT deduction changes
- Senior citizen deduction updates
- And all other provisions in Title 26

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

## Local Development

```bash
# Install
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your keys

# Run
python main.py
```

## Environment Variables

```
GEMINI_API_KEY=your-gemini-key
CHROMA_API_KEY=your-chroma-key
CHROMA_TENANT=your-tenant
CHROMA_DATABASE=your-database
API_KEY=your-api-key
```

## Tech Stack

- **Embeddings**: Google Gemini (`text-embedding-004`)
- **Vector DB**: Chroma Cloud
- **API**: FastAPI
- **Data**: Title 26 - Internal Revenue Code

## License

MIT
