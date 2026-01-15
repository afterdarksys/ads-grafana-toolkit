"""SQLite database for dashboard persistence."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, List, Optional


class Database:
    """SQLite database for storing dashboards and metadata."""

    def __init__(self, db_path: str = "dashboards.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS dashboards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    json_data TEXT NOT NULL,
                    template_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS dashboard_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dashboard_id INTEGER NOT NULL,
                    json_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS datasources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    uid TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_dashboards_uid ON dashboards(uid);
                CREATE INDEX IF NOT EXISTS idx_dashboards_title ON dashboards(title);
                CREATE INDEX IF NOT EXISTS idx_history_dashboard ON dashboard_history(dashboard_id);
            """)

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # Dashboard operations
    def save_dashboard(
        self,
        uid: str,
        title: str,
        json_data: dict,
        description: str = "",
        tags: List[str] = None,
        template_name: str = None,
    ) -> int:
        """Save or update a dashboard."""
        tags = tags or []
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, json_data FROM dashboards WHERE uid = ?",
                (uid,)
            )
            existing = cursor.fetchone()

            if existing:
                # Save history
                conn.execute(
                    "INSERT INTO dashboard_history (dashboard_id, json_data) VALUES (?, ?)",
                    (existing["id"], existing["json_data"])
                )
                # Update existing
                conn.execute("""
                    UPDATE dashboards
                    SET title = ?, description = ?, tags = ?, json_data = ?,
                        template_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE uid = ?
                """, (title, description, json.dumps(tags), json.dumps(json_data),
                      template_name, uid))
                return existing["id"]
            else:
                cursor = conn.execute("""
                    INSERT INTO dashboards (uid, title, description, tags, json_data, template_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (uid, title, description, json.dumps(tags), json.dumps(json_data), template_name))
                return cursor.lastrowid

    def get_dashboard(self, uid: str) -> Optional[dict]:
        """Get a dashboard by UID."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM dashboards WHERE uid = ?",
                (uid,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "uid": row["uid"],
                    "title": row["title"],
                    "description": row["description"],
                    "tags": json.loads(row["tags"]),
                    "json_data": json.loads(row["json_data"]),
                    "template_name": row["template_name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    def list_dashboards(
        self,
        search: str = None,
        tags: List[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List dashboards with optional filtering."""
        with self._get_conn() as conn:
            query = "SELECT id, uid, title, description, tags, template_name, created_at, updated_at FROM dashboards WHERE 1=1"
            params = []

            if search:
                query += " AND (title LIKE ? OR description LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            if tags:
                for tag in tags:
                    query += " AND tags LIKE ?"
                    params.append(f'%"{tag}"%')

            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            return [
                {
                    "id": row["id"],
                    "uid": row["uid"],
                    "title": row["title"],
                    "description": row["description"],
                    "tags": json.loads(row["tags"]),
                    "template_name": row["template_name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in cursor.fetchall()
            ]

    def delete_dashboard(self, uid: str) -> bool:
        """Delete a dashboard."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM dashboards WHERE uid = ?", (uid,))
            return cursor.rowcount > 0

    def get_dashboard_history(self, uid: str, limit: int = 10) -> List[dict]:
        """Get dashboard history."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT h.id, h.json_data, h.created_at
                FROM dashboard_history h
                JOIN dashboards d ON h.dashboard_id = d.id
                WHERE d.uid = ?
                ORDER BY h.created_at DESC
                LIMIT ?
            """, (uid, limit))
            return [
                {
                    "id": row["id"],
                    "json_data": json.loads(row["json_data"]),
                    "created_at": row["created_at"],
                }
                for row in cursor.fetchall()
            ]

    # Datasource operations
    def save_datasource(
        self,
        name: str,
        ds_type: str,
        uid: str = None,
        is_default: bool = False,
    ) -> int:
        """Save or update a datasource."""
        with self._get_conn() as conn:
            # Check if exists
            cursor = conn.execute("SELECT id FROM datasources WHERE name = ?", (name,))
            existing = cursor.fetchone()

            if existing:
                conn.execute("""
                    UPDATE datasources
                    SET type = ?, uid = ?, is_default = ?
                    WHERE name = ?
                """, (ds_type, uid, is_default, name))
                return existing["id"]
            else:
                cursor = conn.execute("""
                    INSERT INTO datasources (name, type, uid, is_default)
                    VALUES (?, ?, ?, ?)
                """, (name, ds_type, uid, is_default))
                return cursor.lastrowid

    def list_datasources(self) -> List[dict]:
        """List all datasources."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM datasources ORDER BY is_default DESC, name")
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "type": row["type"],
                    "uid": row["uid"],
                    "is_default": bool(row["is_default"]),
                }
                for row in cursor.fetchall()
            ]

    def delete_datasource(self, name: str) -> bool:
        """Delete a datasource."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM datasources WHERE name = ?", (name,))
            return cursor.rowcount > 0

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._get_conn() as conn:
            dashboard_count = conn.execute("SELECT COUNT(*) as c FROM dashboards").fetchone()["c"]
            datasource_count = conn.execute("SELECT COUNT(*) as c FROM datasources").fetchone()["c"]
            history_count = conn.execute("SELECT COUNT(*) as c FROM dashboard_history").fetchone()["c"]

            return {
                "dashboards": dashboard_count,
                "datasources": datasource_count,
                "history_entries": history_count,
            }


# Global database instance
_db: Optional[Database] = None


def get_db(db_path: str = None) -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database(db_path or "dashboards.db")
    return _db


def init_db(db_path: str = None) -> Database:
    """Initialize database with custom path."""
    global _db
    _db = Database(db_path or "dashboards.db")
    return _db
