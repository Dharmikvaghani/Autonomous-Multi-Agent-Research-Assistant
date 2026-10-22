import os
import sys
import warnings
import logging
import threading

# Silence annoying PyTorch/transformers import path warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)

# Heavy imports are lazy-loaded inside functions to drastically reduce initial startup time


# -------------------------------------------------------------------
# Beginner-Friendly Explanation:
# This file handles the direct connection to our Vector Database (ChromaDB).
# We use an embedding function to turn text into mathematical vectors.
# By storing vectors instead of plain text, the AI can perform "Semantic Search",
# meaning it can find related ideas based on meaning, not just exact keywords.
# -------------------------------------------------------------------

# Set up the persistent storage location. To avoid SQLite concurrent lock panics
# on Windows (especially when tests run alongside the Streamlit server), we direct
# test scripts to a separate database folder.
is_testing = False
if sys.argv and len(sys.argv) > 0:
    prog_name = os.path.basename(sys.argv[0])
    if "verify_tests" in prog_name or "test_" in prog_name:
        is_testing = True
if os.environ.get("TESTING") == "true":
    is_testing = True

if is_testing:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db_test")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")

_client_lock = threading.RLock()
_ef_lock = threading.RLock()
_cached_client = None
_cached_ef = None
_cached_collections = {}

def get_embedding_function():
    """
    Returns a thread-safe cached instance of Chroma's DefaultEmbeddingFunction.
    """
    global _cached_ef
    if _cached_ef is None:
        with _ef_lock:
            if _cached_ef is None:
                from chromadb.utils import embedding_functions
                _cached_ef = embedding_functions.DefaultEmbeddingFunction()
    return _cached_ef

def get_chroma_client():
    """
    Returns a cached global ChromaDB client to prevent SQLite lock issues.
    """
    global _cached_client
    if _cached_client is None:
        with _client_lock:
            if _cached_client is None:
                import chromadb
                _cached_client = chromadb.PersistentClient(path=DB_PATH)
    return _cached_client

def get_collection_name_for_workspace(workspace: str, suffix: str = "") -> str:
    """
    Standardizes and sanitizes workspace names to valid ChromaDB collection names.
    - Default workspace -> 'research_memory' or 'pdf_documents' (keeps backward compatibility).
    - Custom workspace -> 'ws_{sanitized}' or 'ws_{sanitized}_pdfs'.
    """
    if not workspace or workspace.lower() == "default":
        if suffix == "_pdfs":
            return "pdf_documents"
        return "research_memory"
        
    import re
    # Sanitize workspace name: lowercase, alpha-numeric, underscores and hyphens only
    clean = workspace.lower().strip()
    clean = re.sub(r'[^a-z0-9_-]', '_', clean)
    clean = re.sub(r'_+', '_', clean)
    clean = re.sub(r'-+', '-', clean)
    
    # Ensure starts/ends with alphanumeric
    if not clean or not clean[0].isalnum():
        clean = "ws_" + clean
    if not clean[-1].isalnum():
        clean = clean + "_ws"
        
    clean = clean[:50]
    while len(clean) < 3:
        clean = clean + "_ws"
        
    if suffix == "_pdfs":
        return f"ws_{clean}_pdfs"
    return f"ws_{clean}"

def initialize_chroma(workspace: str = "default"):
    """
    Initializes the ChromaDB client and creates/returns a collection for the workspace.
    """
    global _cached_collections
    collection_name = get_collection_name_for_workspace(workspace)
    
    if collection_name in _cached_collections:
        return _cached_collections[collection_name]
        
    # Load embedding function outside the global client lock to prevent blocking
    # concurrent client requests (like list_workspaces) during model instantiation.
    fast_ef = get_embedding_function()
    
    with _client_lock:
        # Double-check cache lock pattern
        if collection_name in _cached_collections:
            return _cached_collections[collection_name]
            
        client = get_chroma_client()
        
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=fast_ef,
            metadata={"hnsw:space": "cosine"}
        )
        
        _cached_collections[collection_name] = collection
        return collection



def list_workspaces() -> list[str]:
    """
    Queries ChromaDB client to discover all active workspaces based on collection naming.
    """
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        workspaces = ["default"]
        for col in collections:
            if col.name == "research_memory" or col.name == "pdf_documents":
                continue
            if col.name.startswith("ws_"):
                name = col.name[3:]
                if name.endswith("_pdfs"):
                    name = name[:-5]
                workspaces.append(name)
        return sorted(list(set(workspaces)))
    except Exception as e:
        print(f"[ChromaDB Error] Failed to list workspaces: {e}")
        return ["default"]

def store_research_memory(doc_id: str, document_text: str, metadata: dict, workspace: str = "default"):
    """
    Saves a piece of research into the vector database workspace collection.
    """
    collection = initialize_chroma(workspace=workspace)
    
    try:
        collection.add(
            documents=[document_text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        print(f"[ChromaDB] Successfully saved memory: {doc_id} in workspace: {workspace}")
    except Exception as e:
        print(f"[ChromaDB Error] Failed to save memory to workspace {workspace}: {e}")

def search_related_memories(query_text: str, n_results: int = 2, workspace: str = "default"):
    """
    Performs a semantic search to find past research related to the new query in the workspace.
    """
    collection = initialize_chroma(workspace=workspace)
    
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        retrieved_memories = []
        if results and results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                memory = {
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if 'distances' in results else None
                }
                retrieved_memories.append(memory)
                
        return retrieved_memories
        
    except Exception as e:
        print(f"[ChromaDB Error] Failed to search memory in workspace {workspace}: {e}")
        return []

def get_all_memories(workspace: str = "default"):
    """
    Retrieves all memories currently stored in the workspace collection.
    """
    try:
        client = get_chroma_client()
        collection_name = get_collection_name_for_workspace(workspace)
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            return []
            
        results = collection.get()
        retrieved_memories = []
        
        if results and results.get('documents'):
            for i in range(len(results['documents'])):
                memory = {
                    "id": results['ids'][i],
                    "document": results['documents'][i],
                    "metadata": results['metadatas'][i] if results['metadatas'] else {}
                }
                retrieved_memories.append(memory)
                
        retrieved_memories.sort(key=lambda x: x['metadata'].get('timestamp', ''), reverse=True)
        return retrieved_memories
        
    except Exception as e:
        print(f"[ChromaDB Error] Failed to retrieve all memories for workspace {workspace}: {e}")
        return []

# ═══════════════════════════════════════════════════════════════════
#  RAG RETRIEVAL LAYER  —  added to support the full RAG pipeline
# ═══════════════════════════════════════════════════════════════════

def initialize_collection(workspace: str = "default"):
    """
    Public alias for initialize_chroma().
    """
    return initialize_chroma(workspace=workspace)

def add_research_memory(doc_id: str, document_text: str, metadata: dict, workspace: str = "default"):
    """
    Enhanced wrapper for store_research_memory() with workspace routing.
    """
    print(f"[Memory Storage] Encoding and archiving memory: {doc_id} in workspace: {workspace}")
    store_research_memory(doc_id=doc_id, document_text=document_text, metadata=metadata, workspace=workspace)

def retrieve_similar_research(query: str, n_results: int = 3,
                               min_similarity: float = 0.20, workspace: str = "default") -> list[dict]:
    """
    RAG Retrieval Core — finds the top-N semantically similar research records in the workspace.
    """
    print(f"[Memory Retrieval] Searching semantic memory in workspace '{workspace}' for: '{query}'")

    try:
        collection = initialize_chroma(workspace=workspace)

        total_docs = collection.count()
        if total_docs == 0:
            print(f"[Memory Retrieval] Memory bank is empty in workspace '{workspace}' — no past research found.")
            return []

        actual_n = min(n_results, total_docs)

        results = collection.query(
            query_texts=[query],
            n_results=actual_n,
            include=["documents", "metadatas", "distances"]
        )

        retrieved = []

        if not results or not results.get("documents") or not results["documents"][0]:
            print("[Memory Retrieval] No results returned from ChromaDB.")
            return []

        for i in range(len(results["documents"][0])):
            raw_distance = results["distances"][0][i] if results.get("distances") else 1.0
            similarity   = max(0.0, round(1.0 - raw_distance, 4))

            if similarity < min_similarity:
                continue

            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            topic    = metadata.get("topic", "Unknown Topic")

            retrieved.append({
                "id":              results["ids"][0][i],
                "topic":           topic,
                "document":        results["documents"][0][i],
                "metadata":        metadata,
                "similarity_score": similarity,
                "similarity_pct":  f"{similarity * 100:.1f}%",
                "distance":        raw_distance,
            })

        retrieved.sort(key=lambda x: x["similarity_score"], reverse=True)

        print(f"[Memory Retrieval] Found {len(retrieved)} relevant memories in workspace '{workspace}' "
              f"(threshold >= {min_similarity * 100:.0f}%).")
        return retrieved

    except Exception as e:
        print(f"[Memory Retrieval Error] Semantic search failed in workspace '{workspace}': {e}")
        return []
