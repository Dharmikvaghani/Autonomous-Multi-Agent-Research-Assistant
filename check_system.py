"""
Prism AI — System Health & Smoke Test Suite
Verifies all backend components, ChromaDB vector stores, exporters,
and frontend production builds.

Usage:
    python check_system.py
"""

import os
import sys

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

def run_checks():
    print("=" * 65)
    print("  🔍 PRISM AI — SYSTEM HEALTH & VERIFICATION SUITE")
    print("=" * 65)

    passed = 0
    total = 0

    def check(name, fn):
        nonlocal passed, total
        total += 1
        try:
            res = fn()
            if res:
                print(f"  [✓ PASS] {name}: {res}")
            else:
                print(f"  [✓ PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [✗ FAIL] {name}: {e}")

    # 1. Imports
    def test_imports():
        import fastapi
        import chromadb
        import langgraph
        import pydantic
        import fpdf
        return "FastAPI, ChromaDB, LangGraph, Pydantic, FPDF loaded"
    check("Core Dependencies Import", test_imports)

    # 2. ChromaDB Client
    def test_chroma():
        from memory.chroma_store import get_chroma_client
        client = get_chroma_client()
        cols = client.list_collections()
        col_names = [c.name for c in cols]
        counts = {c.name: c.count() for c in cols}
        return f"{len(cols)} collections found {counts}"
    check("ChromaDB Vector Store", test_chroma)

    # 3. Vector Similarity Search
    def test_vector_search():
        from memory.chroma_store import search_related_memories
        results = search_related_memories("multi-agent distributed", n_results=1, workspace="default")
        if not results:
            raise ValueError("No memory results returned from vector search")
        sim = results[0].get("similarity_pct", "N/A")
        return f"Retrieved top match '{results[0].get('id')}' with {sim} similarity"
    check("Semantic Vector Search", test_vector_search)

    # 4. PDF Chunk Retrieval
    def test_pdf_rag():
        from tools.pdf_parser_tool import search_pdf_context
        ctx, chunks = search_pdf_context("collaborative software development", n_results=2, workspace="default")
        if not chunks:
            raise ValueError("No PDF chunks retrieved")
        return f"Retrieved {len(chunks)} chunks (top: {chunks[0].get('similarity_pct')})"
    check("PDF RAG Context Ingestion", test_pdf_rag)

    # 5. LaTeX and BibTeX Generator
    def test_latex():
        from tools.latex_generator import convert_markdown_to_latex, generate_bibtex
        sample_md = "# Title\n## 1. Intro\nAnalysis text.\n- Point 1"
        tex = convert_markdown_to_latex(sample_md, title="Test Report")
        bib = generate_bibtex([{"title": "Sample Paper", "authors": ["Doe, J."], "year": 2024}], title="Test")
        if len(tex) < 100 or len(bib) < 50:
            raise ValueError("LaTeX/BibTeX output too short")
        return f"Generated {len(tex)} chars LaTeX (.tex) and {len(bib)} chars BibTeX (.bib)"
    check("Academic LaTeX & BibTeX Generator", test_latex)

    # 6. PDF Binary Exporter
    def test_pdf_gen():
        from tools.pdf_generator import convert_markdown_to_pdf_bytes
        sample_md = "# Research Paper\n## 1. Executive Summary\nValid report content."
        pdf_bytes = convert_markdown_to_pdf_bytes(sample_md, title="Test Paper")
        if len(pdf_bytes) < 1000:
            raise ValueError("Generated PDF bytes too small")
        return f"Generated {len(pdf_bytes)} bytes binary PDF"
    check("Markdown to PDF Binary Engine", test_pdf_gen)

    # 7. Frontend Production Assets
    def test_frontend_dist():
        dist_html = os.path.join(PROJECT_ROOT, "frontend", "dist", "index.html")
        if not os.path.exists(dist_html):
            raise FileNotFoundError("frontend/dist/index.html not found. Run 'npm run build' inside frontend/")
        size_kb = os.path.getsize(dist_html) / 1024
        return f"Production build verified (index.html: {size_kb:.2f} KB)"
    check("React Frontend Production Bundle", test_frontend_dist)

    # 8. Workspaces Discovery
    def test_workspaces():
        from memory.chroma_store import list_workspaces
        ws = list_workspaces()
        return f"Active isolated workspaces: {ws}"
    check("Multi-Workspace Isolation", test_workspaces)

    print("\n" + "=" * 65)
    print(f"  VERIFICATION RESULTS: {passed}/{total} Passed ({(passed/total)*100:.0f}%)")
    print("=" * 65)
    if passed == total:
        print("  🎉 ALL SYSTEMS OPERATIONAL — READY FOR PRODUCTION DEMO!\n")
    else:
        print("  ⚠️ Some checks failed. Review errors above.\n")

if __name__ == "__main__":
    run_checks()
