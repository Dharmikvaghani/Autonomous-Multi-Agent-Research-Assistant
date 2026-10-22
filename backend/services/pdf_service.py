import os
import json
import urllib.parse
from typing import List, Dict, Any, Optional
from tools.pdf_parser_tool import (
    ingest_pdf_to_chroma,
    search_pdf_context,
    METADATA_FILE,
    DATABASE_DIR
)
from tools.groq_client import ask_groq

STATIC_PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploaded_pdfs")

class PdfService:
    def list_pdfs(self, workspace: str = "default") -> List[Dict[str, Any]]:
        if not os.path.exists(METADATA_FILE):
            return []
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [doc for doc in data if doc.get("workspace", "default") == workspace]
        except Exception:
            return []

    def upload_and_ingest(self, file_bytes: bytes, filename: str, workspace: str = "default") -> Dict[str, Any]:
        os.makedirs(STATIC_PDF_DIR, exist_ok=True)
        pdf_path = os.path.join(STATIC_PDF_DIR, filename)
        with open(pdf_path, "wb") as f:
            f.write(file_bytes)

        record = ingest_pdf_to_chroma(pdf_path=pdf_path, filename=filename, workspace=workspace)
        return record

    def chat_with_pdf(self, query: str, filename: Optional[str] = None, top_k: int = 4, workspace: str = "default") -> Dict[str, Any]:
        metadata_filter = None
        if filename:
            metadata_filter = {"source_file": filename}

        context_str, chunks = search_pdf_context(
            query=query,
            n_results=top_k,
            min_similarity=0.25,
            workspace=workspace,
            metadata_filter=metadata_filter
        )

        if not chunks:
            return {
                "answer": "No relevant content found in the uploaded PDF documents.",
                "sources": []
            }

        prompt = f"""You are an expert AI research assistant.
Answer the user's question accurately using ONLY the provided PDF context excerpts below.
If the provided context does not contain enough information, state that clearly.

--- BEGIN RETRIEVED PDF CONTEXT ---
{context_str}
--- END RETRIEVED PDF CONTEXT ---

USER QUESTION: {query}

Provide a clear, detailed, well-structured markdown answer with headings and bullet points where applicable."""

        raw_answer = ask_groq(prompt)
        sources = []
        for c in chunks:
            meta = c.get("metadata", {})
            sources.append({
                "source_file": meta.get("source_file"),
                "title": meta.get("title"),
                "section": meta.get("section"),
                "similarity": c.get("similarity_pct"),
                "excerpt": c.get("document")
            })

        return {
            "answer": raw_answer,
            "sources": sources
        }

pdf_service = PdfService()
