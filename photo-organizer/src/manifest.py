from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS photos (
    sha256 TEXT PRIMARY KEY,
    dest_path TEXT,
    capture_dt TEXT,
    confidence TEXT NOT NULL,
    source_tag TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('organized', 'review')),
    size_bytes INTEGER,
    organized_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS photo_sources (
    sha256 TEXT NOT NULL REFERENCES photos(sha256),
    origin TEXT NOT NULL,
    origin_path_or_id TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    PRIMARY KEY (sha256, origin, origin_path_or_id)
);

CREATE TABLE IF NOT EXISTS drive_sync_state (
    file_id TEXT PRIMARY KEY,
    name TEXT,
    md5_checksum TEXT,
    last_seen_at TEXT NOT NULL,
    local_cache_path TEXT
);
"""


class Manifest:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Manifest":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- photos ------------------------------------------------------------

    def get_photo(self, sha256: str) -> sqlite3.Row | None:
        cur = self._conn.execute("SELECT * FROM photos WHERE sha256 = ?", (sha256,))
        return cur.fetchone()

    def upsert_photo(
        self,
        sha256: str,
        dest_path: str | None,
        capture_dt: datetime | None,
        confidence: str,
        source_tag: str,
        status: str,
        size_bytes: int,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO photos
                (sha256, dest_path, capture_dt, confidence, source_tag, status, size_bytes, organized_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sha256) DO UPDATE SET
                dest_path=excluded.dest_path,
                capture_dt=excluded.capture_dt,
                confidence=excluded.confidence,
                source_tag=excluded.source_tag,
                status=excluded.status,
                size_bytes=excluded.size_bytes,
                organized_at=excluded.organized_at
            """,
            (
                sha256,
                dest_path,
                capture_dt.isoformat() if capture_dt else None,
                confidence,
                source_tag,
                status,
                size_bytes,
                datetime.now().isoformat(),
            ),
        )
        self._conn.commit()

    def add_photo_source(self, sha256: str, origin: str, origin_path_or_id: str) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO photo_sources (sha256, origin, origin_path_or_id, seen_at)
            VALUES (?, ?, ?, ?)
            """,
            (sha256, origin, origin_path_or_id, datetime.now().isoformat()),
        )
        self._conn.commit()

    def list_by_status(self, status: str) -> list[sqlite3.Row]:
        cur = self._conn.execute("SELECT * FROM photos WHERE status = ?", (status,))
        return cur.fetchall()

    def sources_for(self, sha256: str) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM photo_sources WHERE sha256 = ?", (sha256,)
        )
        return cur.fetchall()

    def counts_by_status(self) -> dict[str, int]:
        cur = self._conn.execute("SELECT status, COUNT(*) as n FROM photos GROUP BY status")
        return {row["status"]: row["n"] for row in cur.fetchall()}

    # -- drive sync state ----------------------------------------------------

    def get_drive_sync_state(self, file_id: str) -> sqlite3.Row | None:
        cur = self._conn.execute(
            "SELECT * FROM drive_sync_state WHERE file_id = ?", (file_id,)
        )
        return cur.fetchone()

    def upsert_drive_sync_state(
        self, file_id: str, name: str, md5_checksum: str | None, local_cache_path: str | None
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO drive_sync_state (file_id, name, md5_checksum, last_seen_at, local_cache_path)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_id) DO UPDATE SET
                name=excluded.name,
                md5_checksum=excluded.md5_checksum,
                last_seen_at=excluded.last_seen_at,
                local_cache_path=excluded.local_cache_path
            """,
            (file_id, name, md5_checksum, datetime.now().isoformat(), local_cache_path),
        )
        self._conn.commit()


@contextmanager
def open_manifest(db_path: Path) -> Iterator[Manifest]:
    m = Manifest(db_path)
    try:
        yield m
    finally:
        m.close()
