"""SQLite storage for dialog context (per-user tables)."""

import json
import sqlite3
from pathlib import Path
from typing import Iterator

# Default user id for single-user mode; later can be extended for multi-user
DEFAULT_USER_ID = "default"

# DB file in project root
DB_PATH = Path(__file__).resolve().parent.parent / "context.db"


def _table_name(user_id: str) -> str:
    """Safe table name for user: context_<user_id> (alphanumeric + underscore)."""
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in user_id) or "default"
    return f"context_{safe}"


class ContextDB:
    """Context storage: one table per user, chronological theses."""

    def __init__(self, db_path: Path | str = DB_PATH):
        self._path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_table(self, user_id: str) -> None:
        table = _table_name(user_id)
        self._connect().execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                user_theses TEXT NOT NULL,
                assistant_theses TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def add_turn(
        self,
        user_id: str,
        user_theses: list[str],
        assistant_theses: list[str],
    ) -> None:
        """Append one dialog turn (theses) for the user."""
        self._ensure_table(user_id)
        table = _table_name(user_id)
        self._connect().execute(
            f"""
            INSERT INTO {table} (user_theses, assistant_theses)
            VALUES (?, ?)
            """,
            (json.dumps(user_theses, ensure_ascii=False), json.dumps(assistant_theses, ensure_ascii=False)),
        )
        self._conn.commit()

    def get_context_text(self, user_id: str) -> str:
        """Return full context as a single text for the model (chronological)."""
        self._ensure_table(user_id)
        table = _table_name(user_id)
        rows = self._connect().execute(
            f"SELECT user_theses, assistant_theses, created_at FROM {table} ORDER BY id ASC"
        ).fetchall()
        parts = []
        for row in rows:
            ut = json.loads(row["user_theses"])
            at = json.loads(row["assistant_theses"])
            for t in ut:
                parts.append(t)
            for t in at:
                parts.append(t)
        return "\n".join(parts)

    def get_all_entries(self, user_id: str) -> Iterator[dict]:
        """Yield all context entries in chronological order (for 'show context')."""
        self._ensure_table(user_id)
        table = _table_name(user_id)
        cur = self._connect().execute(
            f"SELECT id, created_at, user_theses, assistant_theses FROM {table} ORDER BY id ASC"
        )
        for row in cur:
            yield {
                "id": row["id"],
                "created_at": row["created_at"],
                "user_theses": json.loads(row["user_theses"]),
                "assistant_theses": json.loads(row["assistant_theses"]),
            }

    def clear(self, user_id: str) -> None:
        """Remove all context for the user (table cleared, disk reclaimed)."""
        table = _table_name(user_id)
        self._connect().execute(f"DELETE FROM {table}")
        self._conn.commit()
        try:
            old = self._conn.isolation_level
            self._conn.isolation_level = None
            self._conn.execute("VACUUM")
            self._conn.isolation_level = old
        except Exception:
            pass

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
