from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"
    NONE = "none"

    @property
    def rank(self) -> int:
        return _CONFIDENCE_RANK[self]


_CONFIDENCE_RANK = {
    Confidence.NONE: 0,
    Confidence.VERY_LOW: 1,
    Confidence.LOW: 2,
    Confidence.MEDIUM: 3,
    Confidence.HIGH: 4,
}


@dataclass
class DateResolution:
    capture_dt: datetime | None
    confidence: Confidence
    source_tag: str
    detail: str = ""


@dataclass
class DriveFileMeta:
    file_id: str
    name: str
    md5_checksum: str | None
    created_time: str | None
    image_media_time: str | None
    device_hint: str


@dataclass
class PhotoRecord:
    """A single staged, hashable file being run through the pipeline."""

    local_path: Path
    origin: str  # "drive" | "naver_inbox"
    original_name: str
    origin_path_or_id: str
    device_hint: str = "misc"
    drive_meta: DriveFileMeta | None = None
    sha256: str | None = None
    resolution: DateResolution | None = None
    dest_path: Path | None = None
