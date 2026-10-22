import os
import sys

# Ensure site-packages and root directory are on python path
site_pkg = os.path.expanduser(r"~\AppData\Roaming\Python\Python314\site-packages")
if os.path.exists(site_pkg) and site_pkg not in sys.path:
    sys.path.insert(0, site_pkg)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api import api_router

app = FastAPI(
    title="Autonomous Multi-Agent Research Assistant API",
    description="Backend API supporting React.js single-page research assistant application.",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

# Static file serving for uploaded PDFs
static_pdf_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploaded_pdfs")
os.makedirs(static_pdf_dir, exist_ok=True)
app.mount("/static/uploaded_pdfs", StaticFiles(directory=static_pdf_dir), name="uploaded_pdfs")

# Serve React static app if compiled
dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        file_path = os.path.join(dist_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_dir, "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "name": "Autonomous Multi-Agent Research Assistant API",
            "version": "2.0.0",
            "status": "online",
            "docs": "/docs"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
