from __future__ import annotations

from src.manifest import Manifest
from src.models import PhotoRecord


def is_duplicate(manifest: Manifest, sha256: str) -> bool:
    """True if this content hash has already been organized or queued for review.

    Content identity (sha256), not source, is the dedup key: the same photo backed up
    to both Google Drive and Naver Cloud is organized exactly once.
    """
    return manifest.get_photo(sha256) is not None


def register_source(manifest: Manifest, record: PhotoRecord) -> None:
    """Record that this content hash was also seen at this origin, for traceability."""
    assert record.sha256 is not None
    manifest.add_photo_source(record.sha256, record.origin, record.origin_path_or_id)
