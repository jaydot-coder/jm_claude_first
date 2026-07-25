from __future__ import annotations

from pathlib import Path
from typing import Iterator

from src.models import PhotoRecord

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif"}


def scan_inbox(inbox_dir: Path) -> Iterator[PhotoRecord]:
    """Recursively scans a local folder the user manually downloaded Naver Cloud photos
    into. No stable external ID exists here -- dedup/incrementality relies entirely on
    the sha256 content hash computed later in the pipeline."""
    if not inbox_dir.exists():
        return
    for path in sorted(inbox_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _ALLOWED_EXTENSIONS:
            continue
        yield PhotoRecord(
            local_path=path,
            origin="naver_inbox",
            original_name=path.name,
            origin_path_or_id=str(path),
        )
