import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

DB_PATH = config.DATA_DIR / "projects.db"


@contextmanager
def _conn():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id          TEXT PRIMARY KEY,
                subject     TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                rubric      TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  TEXT NOT NULL,
                page        TEXT NOT NULL,
                data        TEXT NOT NULL DEFAULT '{}',
                updated_at  TEXT NOT NULL,
                UNIQUE(project_id, page),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """)


_init_db()


def _now() -> str:
    return datetime.utcnow().isoformat()


# ── Projects ─────────────────────────────────────────────────────────────────

def create_project(subject: str, description: str = "") -> str:
    project_id = uuid.uuid4().hex
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO projects (id, subject, description, rubric, created_at, updated_at) "
            "VALUES (?, ?, ?, '', ?, ?)",
            (project_id, subject.strip(), description.strip(), now, now),
        )
    return project_id


def list_projects() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT p.*, "
            "  (SELECT COUNT(*) FROM conversations c WHERE c.project_id = p.id) AS page_count "
            "FROM projects p ORDER BY p.updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_project(project_id: str) -> Optional[dict]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    return dict(row) if row else None


def update_project(project_id: str, subject: Optional[str] = None, rubric: Optional[str] = None,
                   description: Optional[str] = None) -> None:
    now = _now()
    with _conn() as con:
        if subject is not None:
            con.execute("UPDATE projects SET subject=?, updated_at=? WHERE id=?",
                        (subject.strip(), now, project_id))
        if rubric is not None:
            con.execute("UPDATE projects SET rubric=?, updated_at=? WHERE id=?",
                        (rubric, now, project_id))
        if description is not None:
            con.execute("UPDATE projects SET description=?, updated_at=? WHERE id=?",
                        (description.strip(), now, project_id))


def touch_project(project_id: str) -> None:
    with _conn() as con:
        con.execute("UPDATE projects SET updated_at=? WHERE id=?", (_now(), project_id))


def delete_project(project_id: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM projects WHERE id=?", (project_id,))


# ── Conversations ─────────────────────────────────────────────────────────────

def save_conversation(project_id: str, page: str, data: dict) -> None:
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO conversations (project_id, page, data, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(project_id, page) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
            (project_id, page, json.dumps(data, ensure_ascii=False), now),
        )
    touch_project(project_id)


def load_conversation(project_id: str, page: str) -> dict:
    with _conn() as con:
        row = con.execute(
            "SELECT data FROM conversations WHERE project_id=? AND page=?",
            (project_id, page),
        ).fetchone()
    if row:
        try:
            return json.loads(row["data"])
        except Exception:
            return {}
    return {}


def get_project_pages(project_id: str) -> list[str]:
    with _conn() as con:
        rows = con.execute(
            "SELECT page FROM conversations WHERE project_id=?", (project_id,)
        ).fetchall()
    return [r["page"] for r in rows]
