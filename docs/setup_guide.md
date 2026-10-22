# Setup Guide — Prism AI

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build toolchain |
| npm | 9+ | Package manager (bundled with Node.js) |
| Git | 2.x | Version control |

You also need at least **one LLM API key** from the following providers:
- [Groq](https://console.groq.com/) (recommended — fastest inference)
- [Google Gemini](https://aistudio.google.com/apikey)
- [OpenAI](https://platform.openai.com/api-keys)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/SahilSurani/Autonomous-Multi-Agent-Research-Assistant.git
cd Autonomous-Multi-Agent-Research-Assistant
```

---

## Step 2: Python Environment Setup

Create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate — Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate — Windows (CMD)
.\venv\Scripts\activate.bat

# Activate — macOS/Linux
source venv/bin/activate
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

> **Note:** The first run will download the `all-MiniLM-L6-v2` sentence transformer model (~80 MB). This is cached for subsequent runs.

---

## Step 3: Configure API Keys

Copy the example environment file:
```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
# Primary LLM Engine (required — at least one)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Fallback LLM Engine (optional but recommended)
GEMINI_API_KEY=your_gemini_api_key_here

# Web Search (optional — enables web search tool)
TAVILY_API_KEY=tvly_your_tavily_key_here

# Additional Keys for Rate Limit Rotation (optional)
GROQ_API_KEY_2=gsk_second_key
GROQ_API_KEY_3=gsk_third_key
```

**Supported Providers:**
| Variable | Provider | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Groq | Primary LLM (Llama 3.3 70B) |
| `GEMINI_API_KEY` | Google Gemini | Fallback LLM |
| `OPENAI_API_KEY` | OpenAI | Alternative LLM |
| `NVIDIA_API_KEY` | NVIDIA NIM | Alternative LLM |
| `DEEPSEEK_API_KEY` | DeepSeek | Alternative LLM |
| `XAI_API_KEY` | xAI | Alternative LLM |
| `TAVILY_API_KEY` | Tavily | Web search |
| `SERPER_API_KEY` | Serper | Web search (alternative) |

> **Tip:** You can also add/update API keys at runtime via the Settings panel in the UI.

---

## Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Step 5: Run the Application

### Development Mode (Two Terminals)

**Terminal 1 — Backend:**
```bash
python main.py
```
Backend starts at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
Frontend starts at `http://localhost:5173` with hot-reload.

### Production Mode (Single Server)

```bash
# Build frontend static assets
cd frontend
npm run build
cd ..

# Start server (serves both API + frontend)
python main.py
```
Access the full application at `http://localhost:8000`.

---

## Step 6: Verify Installation

Run the verification test suite:
```bash
python scratch/verify_tests.py
```

Expected output: **80/81 tests passing (99%)**. The single failure is `search_semantic_scholar()` which depends on external API rate limits and is not a code issue.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Ensure your virtual environment is activated |
| Port 8000 in use | Change port: `uvicorn main:app --port 8001` |
| Frontend can't reach backend | Check CORS settings; ensure backend is running on port 8000 |
| Slow first query | Embedding model downloads on first use (~80 MB) |
| LLM rate limit errors | Add multiple API keys (e.g., `GROQ_API_KEY_2`, `GROQ_API_KEY_3`) |
| ChromaDB errors | Delete `memory/chroma_db/` directory and restart |
| Node.js version error | Upgrade to Node.js 18+ |
