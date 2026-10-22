# Deployment Guide — Prism AI

## Local Development Deployment

This is the recommended setup for development and testing.

### Prerequisites
- Python 3.11+, Node.js 18+, at least one LLM API key

### Quick Start
```bash
# 1. Setup Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

# 2. Configure API keys
copy .env.example .env
# Edit .env and add your keys

# 3. Setup frontend
cd frontend && npm install && cd ..

# 4. Start backend
python main.py

# 5. Start frontend (separate terminal)
cd frontend && npm run dev
```

- **Backend:** `http://localhost:8000` (API docs at `/docs`)
- **Frontend:** `http://localhost:5173` (Vite dev server with hot-reload)

---

## Production Deployment (Single Server)

Build the React frontend and serve it from FastAPI as static files.

```bash
# Build frontend
cd frontend
npm run build
cd ..

# Start production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

The application is now served entirely from `http://localhost:8000`:
- FastAPI serves the React SPA from `frontend/dist/`
- API endpoints remain at `/api/*`
- All client-side routes fallback to `index.html` for SPA routing

### Production Considerations

| Concern | Recommendation |
|---------|----------------|
| **Process Management** | Use a process manager like `pm2` or `systemd` |
| **Reverse Proxy** | Place Nginx or Caddy in front of Uvicorn |
| **HTTPS** | Configure SSL certificates via Let's Encrypt |
| **Workers** | Run with multiple workers: `uvicorn main:app --workers 4` |
| **Environment** | Never commit `.env` — use environment variables directly |
| **ChromaDB Data** | Backup `memory/chroma_db/` directory regularly |

---

## Docker Deployment (Optional)

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install and build frontend
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci

COPY frontend/ frontend/
RUN cd frontend && npm run build

# Copy backend code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t prism-ai .
docker run -p 8000:8000 --env-file .env prism-ai
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes* | Primary LLM API key |
| `GEMINI_API_KEY` | Fallback | Google Gemini API key |
| `OPENAI_API_KEY` | Optional | OpenAI API key |
| `NVIDIA_API_KEY` | Optional | NVIDIA NIM API key |
| `DEEPSEEK_API_KEY` | Optional | DeepSeek API key |
| `XAI_API_KEY` | Optional | xAI API key |
| `TAVILY_API_KEY` | Optional | Tavily web search key |
| `SERPER_API_KEY` | Optional | Serper web search key |
| `GROQ_API_KEY_2`, `_3` | Optional | Additional Groq keys for rotation |
| `GEMINI_API_KEY_2`, `_3` | Optional | Additional Gemini keys for rotation |
| `PORT` | Optional | Server port (default: 8000) |
| `HOST` | Optional | Server host (default: 0.0.0.0) |

*At least one LLM API key is required.

---

## Data Storage Locations

| Data | Location | Persistent |
|------|----------|-----------|
| Vector embeddings | `memory/chroma_db/` | Yes |
| PDF metadata | `database/pdf_metadata.json` | Yes |
| Uploaded PDFs | `static/uploaded_pdfs/` | Yes |
| API configuration | `.env` | Yes |
| Frontend build | `frontend/dist/` | Regenerated on build |

---

## Health Check

Verify the deployment is working:

```bash
# Check API is responding
curl http://localhost:8000/api/settings

# Run test suite
python scratch/verify_tests.py
```

Expected: API returns JSON with settings; test suite shows 80/81 passing.
