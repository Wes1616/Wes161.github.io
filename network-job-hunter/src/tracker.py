"""Suivi SQLite des candidatures envoyées, pour éviter les doublons."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.models import ApplicationRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    source TEXT NOT NULL,
    date_posted TEXT NOT NULL,
    date_applied TEXT NOT NULL,
    status TEXT NOT NULL,
    match_score INTEGER NOT NULL,
    cv_path TEXT NOT NULL
);
"""


class Tracker:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def is_known(self, job_id: str) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM applications WHERE job_id = ?", (job_id,)
        )
        return cursor.fetchone() is not None

    def record(self, record: ApplicationRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO applications
                (job_id, title, company, source, date_posted, date_applied,
                 status, match_score, cv_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status = excluded.status,
                date_applied = excluded.date_applied,
                match_score = excluded.match_score,
                cv_path = excluded.cv_path
            """,
            (
                record.job_id,
                record.title,
                record.company,
                record.source,
                record.date_posted.isoformat(),
                record.date_applied.isoformat(),
                record.status,
                record.match_score,
                record.cv_path,
            ),
        )
        self._conn.commit()

    def list_all(self) -> list[sqlite3.Row]:
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.execute(
            "SELECT * FROM applications ORDER BY date_applied DESC"
        )
        return cursor.fetchall()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Tracker":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
