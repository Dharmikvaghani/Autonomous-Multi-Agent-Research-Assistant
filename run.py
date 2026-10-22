"""
Prism AI — Unified Application Runner
Launches both the FastAPI backend and React/Vite frontend in parallel,
checks environment status, auto-seeds the ChromaDB vector database if needed,
and handles graceful shutdown on Ctrl+C.

Usage:
    python run.py
"""

import os
import sys
import time
import signal
import subprocess
import threading

# Force UTF-8 encoding and unbuffered output on Windows to ensure instant log streaming
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

processes = []

def check_and_seed_database():
    """Checks if ChromaDB has data; if empty, runs seed_database."""
    try:
        from memory.chroma_store import get_chroma_client
        client = get_chroma_client()
        cols = client.list_collections()
        total_vectors = sum(c.count() for c in cols)
        if total_vectors == 0:
            print("[*] ChromaDB vector store is empty. Running initial database seeder...")
            from seed_database import seed_database
            seed_database()
        else:
            print(f"[✓] ChromaDB ready ({len(cols)} collections, {total_vectors} vectors stored).")
    except Exception as e:
        print(f"[!] Warning checking ChromaDB status: {e}")

def check_and_seed_auth_database():
    """Checks and initializes SQLite auth database with default user and persistent API keys."""
    try:
        from database.auth_db import init_auth_db, sync_settings_to_env, get_all_system_settings
        init_auth_db()
        sync_settings_to_env()
        settings = get_all_system_settings()
        groq_status = "✓ Configured" if settings.get("GROQ_API_KEY") else "Not set"
        gemini_status = "✓ Configured" if settings.get("GEMINI_API_KEY") else "Not set"
        print(f"[✓] SQLite Auth Database ready (Default login: admin / password123).")
        print(f"[✓] Persistent AI Keys: Groq [{groq_status}], Gemini [{gemini_status}].")
    except Exception as e:
        print(f"[!] Warning checking auth database: {e}")

def stream_output(process, prefix):
    """Streams child process stdout/stderr continuously, preventing pipe buffer deadlocks."""
    while True:
        try:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            line_str = line.strip()
            if line_str:
                try:
                    print(f"[{prefix}] {line_str}", flush=True)
                except Exception:
                    # Ascii-safe fallback if console output encoding fails
                    safe_line = line_str.encode("ascii", "replace").decode("ascii")
                    print(f"[{prefix}] {safe_line}", flush=True)
        except Exception:
            # Crucial: NEVER stop draining the pipe, otherwise the OS pipe buffer fills up and hangs the child process!
            time.sleep(0.05)
            continue

def cleanup_processes(signum=None, frame=None):
    """Terminates all spawned child processes cleanly."""
    print("\n\n[*] Shutting down Prism AI servers gracefully...")
    for p in processes:
        try:
            if sys.platform.startswith("win"):
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                p.terminate()
        except Exception:
            pass
    print("[✓] All processes stopped. Goodbye!\n")
    sys.exit(0)

def main():
    print("=" * 65)
    print("  🌌 PRISM AI — AUTONOMOUS MULTI-AGENT RESEARCH PLATFORM")
    print("=" * 65)
    
    # Register signal handlers for clean exit
    signal.signal(signal.SIGINT, cleanup_processes)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, cleanup_processes)

    # 1. Check ChromaDB and Auth Database
    check_and_seed_database()
    check_and_seed_auth_database()

    # Configure UTF-8 unbuffered environment for child processes
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["PYTHONUNBUFFERED"] = "1"

    # 2. Start Backend
    print("\n[*] Starting FastAPI Backend on http://127.0.0.1:8000...")
    backend_cmd = [sys.executable, "-u", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=child_env
    )
    processes.append(backend_proc)
    threading.Thread(target=stream_output, args=(backend_proc, "Backend"), daemon=True).start()

    # 3. Start Frontend
    print("[*] Starting React / Vite Frontend on http://localhost:5173...")
    npm_cmd = "npm.cmd" if sys.platform.startswith("win") else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=child_env
    )
    processes.append(frontend_proc)
    threading.Thread(target=stream_output, args=(frontend_proc, "Frontend"), daemon=True).start()

    time.sleep(2)

    print("\n" + "=" * 65)
    print("  🚀 PRISM AI IS NOW LIVE!")
    print("=" * 65)
    print("  🖥️  Frontend Dashboard : http://localhost:5173")
    print("  🔌 Backend REST API    : http://127.0.0.1:8000")
    print("  📖 Swagger API Docs    : http://127.0.0.1:8000/docs")
    print("  🔑 Demo Login Account  : admin / password123")
    print("=" * 65)
    print("  Press Ctrl+C at any time to stop both servers.\n")

    # Keep alive
    try:
        while True:
            time.sleep(1)
            # If any process died unexpectedly
            if backend_proc.poll() is not None:
                print("[!] Backend process exited.")
                break
            if frontend_proc.poll() is not None:
                print("[!] Frontend process exited.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_processes()

if __name__ == "__main__":
    main()
