# API Documentation — Prism AI

## Base URL

```
http://localhost:8000/api
```

All endpoints are prefixed with `/api/`. The FastAPI auto-generated interactive docs are available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## Authentication

The API does not require authentication tokens. API keys for LLM providers are configured server-side via `.env` or the Settings endpoint.

---

## Endpoints

### 1. Research Endpoints

#### `POST /api/research/start`
Start a new multi-agent research task.

**Request Body:**
```json
{
  "topic": "Transformer attention mechanism in NLP",
  "target_word_count": 2500,
  "self_correction_rounds": 1,
  "search_provider": "tavily",
  "workspace": "default"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `topic` | string | *required* | Research topic to investigate |
| `target_word_count` | int | 2500 | Target report length (500–10000) |
| `self_correction_rounds` | int | 1 | Number of self-correction iterations (0–3) |
| `search_provider` | string | "tavily" | Web search provider to use |
| `workspace` | string | "default" | ChromaDB workspace for memory isolation |

**Response (200):**
```json
{
  "task_id": "abc123-def456",
  "status": "RUNNING",
  "topic": "Transformer attention mechanism in NLP",
  "created_at": "2026-10-09T15:30:00"
}
```

---

#### `GET /api/research/stream/{task_id}`
Stream real-time agent execution events via Server-Sent Events (SSE).

**Response:** `text/event-stream`

Each SSE event is a JSON object with the current orchestrator state, including task statuses, logs, and partial results. The stream closes when the pipeline reaches `COMPLETED` or `FAILED`.

**Example SSE Event:**
```
data: {"status": "RUNNING", "tasks": {"planner": {"status": "COMPLETED", "duration": 3.2}, "researcher_0": {"status": "RUNNING"}}, "logs": ["[15:30:03] Agent Active: Strategic Planner..."]}
```

---

#### `GET /api/research/status/{task_id}`
Get the current status of a research task (polling alternative to SSE).

**Response (200):**
```json
{
  "task_id": "abc123-def456",
  "status": "COMPLETED",
  "topic": "Transformer attention mechanism in NLP",
  "tasks": {
    "planner": {"name": "1. Strategic Planner Agent", "status": "COMPLETED", "duration": 3.2, "error": null},
    "researcher_0": {"name": "2. Researcher Agent: Subtopic A", "status": "COMPLETED", "duration": 15.1, "error": null}
  },
  "logs": ["[15:30:03] Agent Active: Strategic Planner..."],
  "final_report": "# Research Report\n\n## Executive Summary...",
  "critique": {"overall_score": 8, "clarity": 9, "depth": 7},
  "summary": "This research explores...",
  "duration": 45.3
}
```

---

### 2. Memory Bank Endpoints

#### `GET /api/memory`
List all memory items in a workspace.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | null | Optional semantic search query |
| `workspace` | string | "default" | Workspace to search in |

**Response (200):** Array of `MemoryItemResponse`
```json
[
  {
    "id": "rag_abc123",
    "topic": "Quantum Computing Basics",
    "summary": "An overview of quantum computing...",
    "critique": {"overall_score": 8},
    "full_research": "# Full Report...",
    "metadata": {},
    "created_at": "2026-10-09T15:30:00"
  }
]
```

---

#### `GET /api/memory/{doc_id}`
Get a single memory item by ID.

**Query Parameters:** `workspace` (default: "default")

**Response (200):** `MemoryItemResponse` object

---

#### `DELETE /api/memory/{doc_id}`
Delete a memory item.

**Query Parameters:** `workspace` (default: "default")

**Response (200):**
```json
{"success": true, "message": "Memory rag_abc123 deleted"}
```

---

#### `GET /api/workspaces`
List all available workspaces.

**Response (200):**
```json
{"workspaces": ["default", "project_alpha", "thesis_research"]}
```

---

### 3. PDF Chat Endpoints

#### `POST /api/pdf/upload`
Upload a PDF file for RAG indexing.

**Request:** `multipart/form-data`
| Field | Type | Description |
|-------|------|-------------|
| `file` | File | PDF file to upload |
| `workspace` | string | Target workspace (default: "default") |

**Response (200):** Ingestion record with metadata
```json
{
  "filename": "paper.pdf",
  "title": "Graph Neural Networks for Drug Discovery",
  "chunk_count": 12,
  "sections": ["Abstract", "Introduction", "Methodology", "Results", "Conclusion"],
  "table_count": 3,
  "reference_count": 25,
  "summary": "This paper presents...",
  "timestamp": "2026-10-09T15:30:00"
}
```

---

#### `GET /api/pdf/files`
List all uploaded PDFs in a workspace.

**Query Parameters:** `workspace` (default: "default")

**Response (200):** Array of PDF metadata records

---

#### `POST /api/pdf/chat`
Chat with uploaded PDFs using RAG retrieval.

**Query Parameters:** `workspace` (default: "default")

**Request Body:**
```json
{
  "query": "What methodology was used in the paper?",
  "filename": "paper.pdf",
  "top_k": 4
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | *required* | Natural language question |
| `filename` | string | null | Specific PDF to query (null = all PDFs) |
| `top_k` | int | 4 | Number of context chunks to retrieve |

**Response (200):**
```json
{
  "answer": "The paper uses a Graph Convolutional Network (GCN) approach with...",
  "sources": [
    {
      "document": "...relevant chunk text...",
      "metadata": {"title": "paper.pdf", "section": "Methodology"},
      "similarity_score": 0.92
    }
  ]
}
```

---

### 4. Export Endpoint

#### `POST /api/export/pdf`
Convert markdown content to a downloadable PDF file.

**Request Body:**
```json
{
  "title": "Research Report on Quantum Computing",
  "markdown_content": "# Report\n\n## Executive Summary\n..."
}
```

**Response:** Binary PDF file (`application/pdf`) with `Content-Disposition: attachment` header.

---

### 5. Settings Endpoints

#### `GET /api/settings`
Get current system configuration status.

**Response (200):**
```json
{
  "api_keys": {
    "groq": true,
    "gemini": true,
    "openai": false,
    "tavily": true,
    "serper": false,
    "xai": false,
    "nvidia": false,
    "deepseek": false
  },
  "key_counts": {
    "groq": 3,
    "gemini": 2
  },
  "available_workspaces": ["default", "project_alpha"]
}
```

---

#### `POST /api/settings`
Update API keys and configuration. Only non-null fields are updated.

**Request Body:**
```json
{
  "groq_api_key": "gsk_new_key_here",
  "gemini_api_key": "new_gemini_key",
  "tavily_api_key": "tvly_new_key"
}
```

Supported fields: `groq_api_key`, `groq_api_key_2`, `groq_api_key_3`, `gemini_api_key`, `gemini_api_key_2`, `gemini_api_key_3`, `openai_api_key`, `tavily_api_key`, `serper_api_key`, `xai_api_key`, `nvidia_api_key`, `deepseek_api_key`, `active_workspace`.

**Response (200):**
```json
{"success": true, "message": "Settings updated successfully (3 keys saved)"}
```

---

## Error Handling

All errors follow standard HTTP status codes:

| Code | Description |
|------|-------------|
| 400 | Bad request (empty topic, invalid file type, etc.) |
| 404 | Resource not found (invalid task_id, doc_id) |
| 500 | Internal server error |

Error response format:
```json
{"detail": "Error description message"}
```
