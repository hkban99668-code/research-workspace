import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "papers.db")

def _migrate(conn):
    """Add new columns for existing databases."""
    analyses_cols = {row[1] for row in conn.execute("PRAGMA table_info(analyses)")}
    for col in ("key_steps", "innovation"):
        if col not in analyses_cols:
            conn.execute(f"ALTER TABLE analyses ADD COLUMN {col} TEXT")
    if "analysis_type" not in analyses_cols:
        conn.execute("ALTER TABLE analyses ADD COLUMN analysis_type TEXT DEFAULT 'normal'")

    papers_cols = {row[1] for row in conn.execute("PRAGMA table_info(papers)")}
    for col in ("title_zh", "abstract_zh"):
        if col not in papers_cols:
            conn.execute(f"ALTER TABLE papers ADD COLUMN {col} TEXT")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS papers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id    TEXT UNIQUE,
                title       TEXT NOT NULL,
                authors     TEXT,
                abstract    TEXT,
                url         TEXT,
                pdf_url     TEXT,
                source      TEXT,
                published   TEXT,
                fetched_at  TEXT,
                keywords    TEXT,
                is_downloaded INTEGER DEFAULT 0,
                local_path  TEXT,
                is_starred       INTEGER DEFAULT 0,
                is_read          INTEGER DEFAULT 0,
                title_zh         TEXT,
                abstract_zh      TEXT
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id      INTEGER REFERENCES papers(id),
                summary       TEXT,
                contributions TEXT,
                key_steps     TEXT,
                innovation    TEXT,
                ideas         TEXT,
                analysis_type TEXT DEFAULT 'normal',
                created_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id    INTEGER REFERENCES papers(id),
                type        TEXT NOT NULL,
                model       TEXT,
                digest      TEXT,
                file_path   TEXT,
                created_at  TEXT,
                ended_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS session_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER REFERENCES sessions(id),
                role        TEXT NOT NULL,
                content     TEXT,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS fetch_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at  TEXT,
                source      TEXT,
                count       INTEGER,
                status      TEXT
            );
        """)
        _migrate(conn)

# ── Papers ────────────────────────────────────────────────────────────────────

def upsert_paper(p: dict) -> int:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM papers WHERE paper_id = ?", (p["paper_id"],)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute("""
            INSERT INTO papers (paper_id, title, authors, abstract, url, pdf_url,
                                source, published, fetched_at, keywords)
            VALUES (:paper_id, :title, :authors, :abstract, :url, :pdf_url,
                    :source, :published, :fetched_at, :keywords)
        """, {**p, "fetched_at": datetime.now().isoformat()})
        return cur.lastrowid

def get_papers(source=None, starred=None, unread=None, date=None, limit=100, offset=0):
    clauses, params = [], []
    if source:
        clauses.append("source = ?"); params.append(source)
    if starred is not None:
        clauses.append("is_starred = ?"); params.append(int(starred))
    if unread:
        clauses.append("is_read = 0")
    if date:
        clauses.append("DATE(fetched_at) = ?"); params.append(date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM papers {where} ORDER BY fetched_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()
    return [dict(r) for r in rows]

def get_paper(paper_db_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_db_id,)).fetchone()
    return dict(row) if row else None

def update_paper(paper_db_id: int, **kwargs):
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    with get_conn() as conn:
        conn.execute(f"UPDATE papers SET {sets} WHERE id = ?",
                     list(kwargs.values()) + [paper_db_id])

# ── Analyses ──────────────────────────────────────────────────────────────────

def save_analysis(paper_db_id: int, summary: str, contributions: str,
                  key_steps: str, innovation: str, ideas: str,
                  analysis_type: str = "normal"):
    with get_conn() as conn:
        conn.execute("DELETE FROM analyses WHERE paper_id = ?", (paper_db_id,))
        conn.execute("""
            INSERT INTO analyses (paper_id, summary, contributions, key_steps,
                                  innovation, ideas, analysis_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (paper_db_id, summary, contributions, key_steps, innovation, ideas,
              analysis_type, datetime.now().isoformat()))

def get_analysis(paper_db_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE paper_id = ?", (paper_db_id,)
        ).fetchone()
    return dict(row) if row else None

# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(paper_id: int, session_type: str, model: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (paper_id, type, model, created_at) VALUES (?, ?, ?, ?)",
            (paper_id, session_type, model, datetime.now().isoformat())
        )
        return cur.lastrowid

def add_session_message(session_id: int, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO session_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now().isoformat())
        )

def get_session(session_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(row) if row else None

def get_session_messages(session_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM session_messages WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def update_session(session_id: int, **kwargs):
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    with get_conn() as conn:
        conn.execute(f"UPDATE sessions SET {sets} WHERE id = ?",
                     list(kwargs.values()) + [session_id])

def get_paper_sessions(paper_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE paper_id = ? ORDER BY created_at DESC",
            (paper_id,)
        ).fetchall()
    return [dict(r) for r in rows]

# ── Misc ──────────────────────────────────────────────────────────────────────

def log_fetch(source: str, count: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO fetch_logs (fetched_at, source, count, status) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), source, count, status)
        )

def get_stats():
    with get_conn() as conn:
        total    = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        today    = conn.execute("SELECT COUNT(*) FROM papers WHERE DATE(fetched_at) = DATE('now')").fetchone()[0]
        starred  = conn.execute("SELECT COUNT(*) FROM papers WHERE is_starred = 1").fetchone()[0]
        analyzed = conn.execute("SELECT COUNT(DISTINCT paper_id) FROM analyses").fetchone()[0]
    return {"total": total, "today": today, "starred": starred, "analyzed": analyzed}
