"""
Prism AI — User Authentication Database Module
Handles SQLite-backed user registration, credential hashing with salt,
and session management.
"""

import os
import sqlite3
import hashlib
import secrets
import datetime
from typing import Optional, Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "database", "auth.db")

def _get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
    except Exception:
        pass
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000
    ).hex()
    return hashed, salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a plain password against the stored hash and salt."""
    hashed, _ = hash_password(password, salt)
    return secrets.compare_digest(hashed, password_hash)

def init_auth_db():
    """Initializes the users and sessions tables in SQLite and creates a default admin account."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'researcher',
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # Seed default system settings if not present in database
    default_keys = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "PORT": os.getenv("PORT", "8000"),
        "HOST": os.getenv("HOST", "0.0.0.0")
    }
    now_iso = datetime.datetime.utcnow().isoformat()
    for k, v in default_keys.items():
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (k,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (k, v, now_iso)
            )
    conn.commit()

    # Seed default administrator if users table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count == 0:
        salt = secrets.token_hex(16)
        pwd_hash, _ = hash_password("password123", salt)
        now = datetime.datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, salt, full_name, role, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "admin",
            "admin@prism.ai",
            pwd_hash,
            salt,
            "Prism Lead Researcher",
            "Lead Analyst",
            now,
            now
        ))
        conn.commit()
        print("[Auth DB] Initialized SQLite auth database. Created default account: admin / password123")

    conn.close()

    # Always ensure environment variables and .env file are synchronized
    sync_settings_to_env()

def register_user(username: str, email: str, password: str, full_name: Optional[str] = None, role: str = "researcher") -> Dict[str, Any]:
    """Registers a new user in the SQLite database."""
    username = username.strip().lower()
    email = email.strip().lower()

    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if not email or "@" not in email:
        raise ValueError("Please provide a valid email address.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    conn = _get_connection()
    cursor = conn.cursor()

    # Check for existing username or email
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise ValueError("A user with this username or email already exists.")

    salt = secrets.token_hex(16)
    pwd_hash, _ = hash_password(password, salt)
    now = datetime.datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO users (username, email, password_hash, salt, full_name, role, created_at, last_login)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        username,
        email,
        pwd_hash,
        salt,
        full_name.strip() if full_name else username.capitalize(),
        role,
        now,
        now
    ))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "full_name": full_name or username.capitalize(),
        "role": role,
        "created_at": now
    }

def authenticate_user(username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates user credentials against the SQLite database."""
    identifier = username_or_email.strip().lower()
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, password_hash, salt, full_name, role, created_at, last_login
        FROM users
        WHERE username = ? OR email = ?
    """, (identifier, identifier))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    if not verify_password(password, row["password_hash"], row["salt"]):
        conn.close()
        return None

    now = datetime.datetime.utcnow().isoformat()
    cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, row["id"]))
    conn.commit()

    user_data = {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "created_at": row["created_at"],
        "last_login": now
    }
    conn.close()
    return user_data

def create_session(user_id: int, days_valid: int = 7) -> str:
    """Creates a session token for the user in the SQLite database."""
    token = secrets.token_urlsafe(32)
    now = datetime.datetime.utcnow()
    expires = now + datetime.timedelta(days=days_valid)

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    """, (token, user_id, now.isoformat(), expires.isoformat()))
    conn.commit()
    conn.close()
    return token

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile associated with an active session token."""
    if not token:
        return None

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.id, u.username, u.email, u.full_name, u.role, u.created_at, u.last_login, s.expires_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
    """, (token,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    expires = datetime.datetime.fromisoformat(row["expires_at"])
    if datetime.datetime.utcnow() > expires:
        # Expired token: cleanup
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    user_data = {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "created_at": row["created_at"],
        "last_login": row["last_login"]
    }
    conn.close()
    return user_data

def delete_session(token: str) -> bool:
    """Deletes a session token on logout."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def list_users() -> List[Dict[str, Any]]:
    """Returns list of registered users."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, created_at, last_login FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    users = [dict(r) for r in rows]
    conn.close()
    return users

# -------------------------------------------------------------------
# PERSISTENT SYSTEM SETTINGS & ENVIRONMENT SYNC
# -------------------------------------------------------------------

def set_system_setting(key: str, value: str):
    """Saves a key-value setting permanently to SQLite."""
    conn = _get_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO system_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key.strip(), value.strip(), now_iso))
    conn.commit()
    conn.close()
    sync_settings_to_env()

def get_system_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieves a setting value from SQLite."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def get_all_system_settings() -> Dict[str, str]:
    """Retrieves all persistent key-value settings from SQLite."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def sync_settings_to_env():
    """
    Synchronizes persistent settings from SQLite with os.environ and the root .env file.
    Ensures API keys are never lost across server restarts or user account switches.
    Only modifies .env on disk if configuration values actually changed.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings")
    db_settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()

    env_path = os.path.join(PROJECT_ROOT, ".env")
    file_env = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        file_env[k.strip()] = v.strip()
        except Exception:
            pass

    # Merge: SQLite values take priority, but any extra keys from .env are also imported
    merged = {**file_env, **db_settings}

    # Ensure os.environ is populated
    for k, v in merged.items():
        if v:
            os.environ[k] = v

    # Write back to .env ONLY IF content actually differs from file on disk
    if not os.path.exists(env_path) or file_env != merged:
        try:
            lines = [
                "# Prism AI Environment Configuration (Auto-synced with SQLite)\n\n"
            ]
            for k, v in sorted(merged.items()):
                if v:
                    lines.append(f"{k}={v}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"[Auth DB Warning] Could not write .env file: {e}")

    # Invalidate Groq client cached keys
    try:
        from tools.groq_client import _invalidate_key_cache
        _invalidate_key_cache()
    except Exception:
        pass

# Ensure database tables and settings sync exist when module is imported
init_auth_db()

