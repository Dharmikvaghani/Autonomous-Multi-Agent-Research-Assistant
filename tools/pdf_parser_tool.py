"""
PDF Ingestion & Parsing Tool Module
Reads, validates, extracts sections/tables/references from academic PDFs.
Chunks content semantically or using sliding windows, and stores vectors in ChromaDB.
"""

import os
import re
import json
import time
import logging
import fitz  # PyMuPDF
from datetime import datetime

# Setup module logger
logger = logging.getLogger(__name__)

# Constants
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
METADATA_FILE = os.path.join(DATABASE_DIR, "pdf_metadata.json")

def validate_pdf(pdf_path: str) -> bool:
    """
    Validates if a PDF file exists, is not corrupted, and contains readable pages.
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF validation failed: File '{pdf_path}' does not exist.")
        return False
        
    try:
        # Check PyMuPDF opening
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        
        if page_count == 0:
            logger.error(f"PDF validation failed: '{pdf_path}' contains zero pages.")
            return False
            
        return True
    except Exception as e:
        logger.error(f"PDF validation failed: '{pdf_path}' is corrupted or unreadable. Detail: {e}")
        return False

def validate_text_quality(text: str) -> bool:
    """
    Checks if extracted text is valid and not empty or garbage.
    Ensures at least 60% of characters are printable.
    """
    if not text or len(text.strip()) < 100:
        return False
        
    # Check printable characters ratio
    printable_chars = sum(c.isalnum() or c.isspace() or c in ",.-_()[]{}!?:;'/\"+=*" for c in text)
    ratio = printable_chars / len(text)
    
    if ratio < 0.6:
        logger.warning(f"Text quality warning: Only {ratio * 100:.1f}% of characters are printable. Possible scanned image or obfuscated font.")
        return False
        
    return True

def extract_pdf_text_and_sections(pdf_path: str) -> dict:
    """
    Extracts all text from PDF and segments it into logical academic sections.
    """
    if not validate_pdf(pdf_path):
        raise ValueError("Corrupted, empty, or invalid PDF document.")
        
    doc = fitz.open(pdf_path)
    
    # 1. Extract metadata title/author if available in fitz
    metadata_title = doc.metadata.get("title", "")
    
    # 2. Extract full text page by page
    full_text_lines = []
    for page in doc:
        page_text = page.get_text("text")
        full_text_lines.extend(page_text.split("\n"))
        
    doc.close()
    
    # Filter out empty or whitespace-only lines
    lines = [line.strip() for line in full_text_lines if line.strip()]
    
    # 3. Categorize lines into sections
    # Regex to match academic sections
    header_regex = re.compile(
        r'^\s*(?:(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.?\s+|(?:\d+(?:\.\d+)*)\.?\s+)?'
        r'(Abstract|Introduction|Related\s+Work|Methodology|Method|Proposed\s+Approach|Proposed\s+System|Proposed\s+Method|Experiments?|Evaluations?|Results?|Discussions?|Conclusions?|References|Bibliography)'
        r'\s*$', re.IGNORECASE
    )
    
    # Guess paper title (first prominent line if metadata is empty)
    inferred_title = ""
    for line in lines[:5]:
        if len(line) > 15 and not line.lower().startswith("issn") and not "journal" in line.lower():
            inferred_title = line
            break
            
    title = metadata_title.strip() if metadata_title and len(metadata_title.strip()) > 5 else inferred_title
    if not title:
        title = os.path.basename(pdf_path).replace(".pdf", "").replace("_", " ").title()
        
    sections = {}
    current_section = "Header/Title"
    sections[current_section] = []
    
    for line in lines:
        match = header_regex.match(line)
        if match:
            header_name = match.group(1).title()
            # Normalize headers
            if "Bibliography" in header_name or "References" in header_name:
                header_name = "References"
            elif "Method" in header_name:
                header_name = "Methodology"
            elif "Experiment" in header_name or "Evaluation" in header_name:
                header_name = "Experiments"
                
            current_section = header_name
            if current_section not in sections:
                sections[current_section] = []
        else:
            sections[current_section].append(line)
            
    # Combine lines for each section
    final_sections = {}
    for sec, sec_lines in sections.items():
        text_val = "\n".join(sec_lines)
        if text_val.strip():
            final_sections[sec] = text_val
            
    # Extract references list if References section exists
    references = []
    if "References" in final_sections:
        ref_text = final_sections["References"]
        # Split by typical reference indices [1], [2] or newlines
        refs_split = re.split(r'\n(?=\[\d+\])', ref_text)
        if len(refs_split) <= 1:
            refs_split = [r.strip() for r in ref_text.split('\n') if r.strip() and len(r.strip()) > 15]
        else:
            refs_split = [r.strip().replace('\n', ' ') for r in refs_split if r.strip()]
        references = refs_split
        
    # Extract tables
    tables = extract_tables_as_markdown(pdf_path)
    
    all_text = "\n\n".join(final_sections.values())
    if not validate_text_quality(all_text):
        logger.warning("Extracted text failed quality check (possibly scanned/image-only PDF).")
        
    return {
        "title": title,
        "sections": final_sections,
        "references": references,
        "tables": tables,
        "raw_text": all_text
    }

def extract_tables_as_markdown(pdf_path: str) -> list:
    """
    Extracts tables from a PDF using PyMuPDF and formats them as markdown tables.
    """
    tables_md = []
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc, start=1):
            tables = page.find_tables()
            for tab_idx, table in enumerate(tables.tables):
                data = table.extract()
                if not data or not any(data):
                    continue
                    
                # Build header row
                headers = [str(cell or "").strip() for cell in data[0]]
                headers = [h if h else f"Column {i+1}" for i, h in enumerate(headers)]
                
                md_rows = []
                md_rows.append("| " + " | ".join(headers) + " |")
                md_rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
                
                # Build data rows
                for row in data[1:]:
                    cells = [str(cell or "").strip().replace("\n", " ").replace("|", "\\|") for cell in row]
                    if len(cells) < len(headers):
                        cells += [""] * (len(headers) - len(cells))
                    elif len(cells) > len(headers):
                        cells = cells[:len(headers)]
                    md_rows.append("| " + " | ".join(cells) + " |")
                    
                tables_md.append(f"### Table {tab_idx+1} on Page {page_num}\n" + "\n".join(md_rows))
        doc.close()
    except Exception as e:
        logger.warning(f"Table extraction failed: {e}")
        
    return tables_md

def chunk_document(sections: dict, strategy: str = "semantic", chunk_size: int = 1200, overlap: int = 200) -> list:
    """
    Chunks document text using either a semantic (paragraph/section boundaries)
    or sliding window (sentence sliding) chunking strategy.
    """
    chunks = []
    
    if strategy == "semantic":
        # Semantic paragraph-boundary chunker
        for sec_name, text in sections.items():
            if sec_name == "References":
                continue  # References are not chunked for standard semantic reading
                
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
                
            current_chunk = ""
            for p in paragraphs:
                # If paragraph exceeds chunk size, split it by sentence sliding
                if len(p) > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', p)
                    for s in sentences:
                        if len(current_chunk) + len(s) + 1 <= chunk_size:
                            current_chunk += " " + s if current_chunk else s
                        else:
                            if current_chunk:
                                chunks.append({
                                    "text": current_chunk.strip(),
                                    "section": sec_name
                                })
                            # Slide window using overlap
                            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                            current_chunk = (overlap_text + " " + s).strip()
                else:
                    if len(current_chunk) + len(p) + 2 <= chunk_size:
                        current_chunk += "\n\n" + p if current_chunk else p
                    else:
                        if current_chunk:
                            chunks.append({
                                "text": current_chunk.strip(),
                                "section": sec_name
                            })
                        overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                        current_chunk = (overlap_text + "\n\n" + p).strip()
                        
            if current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "section": sec_name
                })
                
    else:
        # Sliding window sentence chunker
        all_text = ""
        for sec_name, text in sections.items():
            if sec_name != "References":
                all_text += f"\n\n--- SECTION: {sec_name} ---\n{text}"
                
        sentences = re.split(r'(?<=[.!?])\s+', re.sub(r'\s+', ' ', all_text).strip())
        current_chunk = []
        current_len = 0
        
        for s in sentences:
            current_chunk.append(s)
            current_len += len(s) + 1
            
            while current_len > chunk_size:
                chunks.append({
                    "text": " ".join(current_chunk).strip(),
                    "section": "General Content"
                })
                # Slide window: pop first elements
                while len(current_chunk) > 1 and current_len - len(current_chunk[0]) - 1 > overlap:
                    removed = current_chunk.pop(0)
                    current_len -= len(removed) + 1
                if len(current_chunk) == 1 and current_len > chunk_size:
                    current_chunk = []
                    current_len = 0
                    break
                    
        if current_chunk:
            chunks.append({
                "text": " ".join(current_chunk).strip(),
                "section": "General Content"
            })
            
    return chunks

def generate_pdf_summary_preview(title: str, abstract: str, introduction: str) -> str:
    """
    Generates a concise 150-200 word summary preview of the PDF using Groq.
    """
    if not abstract and not introduction:
        return "No Abstract or Introduction content available to summarize."
        
    prompt = f"""You are a scientific research assistant.
Your task is to summarize the following academic paper based on its Abstract and Introduction.

Title: {title}

Abstract:
{abstract[:2000]}

Introduction:
{introduction[:2000]}

Provide a concise, high-level executive summary of this paper (max 200 words) highlighting its core objective, methodology, and key contributions. Output ONLY the summary. Do not add comments or filler.
"""
    try:
        from tools.groq_client import ask_groq
        summary = ask_groq(prompt).strip()
        if summary and not summary.startswith("⚠️"):
            return summary
    except Exception as e:
        logger.warning(f"Summary generation failed: {e}")
        
    # Return a basic slice fallback if Groq fails
    fallback = abstract if abstract else introduction
    return fallback[:300] + "..." if len(fallback) > 300 else fallback

def ingest_pdf_to_chroma(pdf_path: str, filename: str, strategy: str = "semantic", workspace: str = "default") -> dict:
    """
    Orchestrates the ingestion workflow:
    Parses PDF -> Chunks text -> Stores in ChromaDB -> Generates metadata cache.
    """
    print(f"[*] PDF Ingestion: Initializing parsing for '{filename}' in workspace '{workspace}'...")
    parsed_data = extract_pdf_text_and_sections(pdf_path)
    title = parsed_data["title"]
    sections = parsed_data["sections"]
    
    # 1. Chunk document
    print(f"[*] PDF Ingestion: Creating chunks using strategy '{strategy}'...")
    chunks = chunk_document(sections, strategy=strategy)
    
    # 2. Store chunks in ChromaDB dedicated pdf_documents collection
    print(f"[*] PDF Ingestion: Storing {len(chunks)} chunks in ChromaDB...")
    try:
        from memory.chroma_store import get_chroma_client, get_collection_name_for_workspace, get_embedding_function
        client = get_chroma_client()
        fast_ef = get_embedding_function()
        
        collection_name = get_collection_name_for_workspace(workspace, suffix="_pdfs")
        pdf_collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=fast_ef,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Ingest chunks in a single batch operation
        batch_documents = []
        batch_metadatas = []
        batch_ids = []
        for idx, chunk in enumerate(chunks):
            chunk_id = f"pdf_{filename.replace('.', '_')}_chunk_{idx}"
            chunk_text = chunk["text"]
            chunk_section = chunk["section"]
            
            # Contextual metadata
            metadata = {
                "source_file": filename,
                "title": title,
                "section": chunk_section,
                "chunk_index": str(idx),
                "timestamp": datetime.now().isoformat(),
                "workspace": workspace
            }
            
            batch_documents.append(chunk_text)
            batch_metadatas.append(metadata)
            batch_ids.append(chunk_id)
            
        if batch_documents:
            pdf_collection.add(
                documents=batch_documents,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
    except Exception as e:
        logger.error(f"Failed to store PDF chunks in ChromaDB: {e}", exc_info=True)
        raise e
        
    # 3. Generate summary preview
    abstract = sections.get("Abstract", "")
    intro = sections.get("Introduction", "")
    print("[*] PDF Ingestion: Generating executive summary preview...")
    summary = generate_pdf_summary_preview(title, abstract, intro)
    
    # 4. Save metadata record to database/pdf_metadata.json
    os.makedirs(DATABASE_DIR, exist_ok=True)
    metadata_list = []
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                metadata_list = json.load(f)
        except Exception:
            metadata_list = []
            
    # Check if document already exists, remove it if so (overwrite)
    metadata_list = [m for m in metadata_list if m["filename"] != filename]
    
    record = {
        "filename": filename,
        "title": title,
        "chunk_count": len(chunks),
        "sections": list(sections.keys()),
        "table_count": len(parsed_data["tables"]),
        "reference_count": len(parsed_data["references"]),
        "summary": summary,
        "timestamp": datetime.now().isoformat(),
        "workspace": workspace
    }
    metadata_list.append(record)
    
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=4)
        
    print(f"[*] PDF Ingestion: Successfully ingested '{filename}' in workspace '{workspace}' (Title: '{title}', {len(chunks)} chunks, {len(parsed_data['tables'])} tables).")
    return record

def search_pdf_context(query: str, n_results: int = 5, min_similarity: float = 0.40, workspace: str = "default", metadata_filter: dict = None) -> tuple:
    """
    Queries the pdf_documents collection in ChromaDB for chunks related to a search query.
    Returns formatted context block and raw retrieved chunk items.
    """
    try:
        from memory.chroma_store import get_chroma_client, get_collection_name_for_workspace
        client = get_chroma_client()
        
        collection_name = get_collection_name_for_workspace(workspace, suffix="_pdfs")
        # Check if collection exists
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            return "", []
            
        total_docs = collection.count()
        if total_docs == 0:
            return "", []
            
        actual_n = min(n_results, total_docs)
        
        # Query collection
        query_kwargs = {
            "query_texts": [query],
            "n_results": actual_n,
            "include": ["documents", "metadatas", "distances"]
        }
        if metadata_filter:
            query_kwargs["where"] = metadata_filter
            
        results = collection.query(**query_kwargs)
        
        retrieved_chunks = []
        if not results or not results.get("documents") or not results["documents"][0]:
            return "", []
            
        for i in range(len(results["documents"][0])):
            raw_dist = results["distances"][0][i] if results.get("distances") else 1.0
            similarity = max(0.0, round(1.0 - raw_dist, 4))
            
            if similarity < min_similarity:
                continue
                
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            
            retrieved_chunks.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": metadata,
                "similarity_score": similarity,
                "similarity_pct": f"{similarity * 100:.1f}%"
            })
            
        if not retrieved_chunks:
            return "", []
            
        # Build context string
        context_lines = [
            "### RETRIEVED UPLOADED PDF LITERATURE CONTEXT (RAG) ###",
            "The following context chunks were extracted from user-provided PDF files matching this query.",
            "Integrate details from these documents as solid peer-reviewed ground truth.",
            ""
        ]
        
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            meta = chunk["metadata"]
            title = meta.get("title", "PDF Document")
            filename = meta.get("source_file", "document.pdf")
            import urllib.parse
            safe_filename = urllib.parse.quote(filename)
            pdf_url = f"/app/static/uploaded_pdfs/{safe_filename}"
            
            context_lines.append(f"[{idx}] Paper Title: {title} | Source URL: {pdf_url} | Section: {meta.get('section')}")
            context_lines.append(f"    Relevance: {chunk['similarity_pct']}")
            context_lines.append(f"    Excerpt: {chunk['document']}")
            context_lines.append("")
            
        context_lines.append("### END OF UPLOADED PDF CONTEXT ###")
        return "\n".join(context_lines), retrieved_chunks
        
    except Exception as e:
        logger.error(f"Failed to query PDF collection: {e}")
        return "", []

if __name__ == "__main__":
    print("=== Testing PDF Parser Module ===")
    print("PDF Parser Tool loaded successfully.")
