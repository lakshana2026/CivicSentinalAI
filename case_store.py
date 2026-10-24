
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "civicsentinel.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint TEXT NOT NULL,
                department TEXT NOT NULL,
                priority TEXT NOT NULL,
                priority_score INTEGER NOT NULL,
                sentiment TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT 'Unknown'
            )
        """)

        # Safe migration for databases created before location existed.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(cases)"
            ).fetchall()
        }

        if "location" not in columns:
            connection.execute("""
                ALTER TABLE cases
                ADD COLUMN location TEXT NOT NULL DEFAULT 'Unknown'
            """)


def save_case(
    complaint,
    department,
    priority,
    priority_score,
    sentiment,
    location="Unknown",
):
    created_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    location = str(location or "").strip() or "Unknown"

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO cases (
                complaint, department, priority,
                priority_score, sentiment, status,
                created_at, location
            )
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)
        """, (
            complaint,
            department,
            priority,
            int(priority_score),
            sentiment,
            created_at,
            location,
        ))

        return cursor.lastrowid


def get_cases():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM cases ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def update_case_status(case_id, status):
    allowed_statuses = {
        "Open", "In Progress", "Resolved", "Escalated"
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid case status")

    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE cases
            SET status = ?
            WHERE id = ?
        """, (status, int(case_id)))

        return cursor.rowcount > 0
