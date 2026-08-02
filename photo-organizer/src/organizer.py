from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.config import Config, ensure_directories
from src.dateresolve import resolve_date
from src.dedup import is_duplicate, register_source
from src.drive_client import sync_all_sources
from src.hashing import sha256_file
from src.manifest import Manifest
from src.models import DateResolution, PhotoRecord
from src.naver_inbox import scan_inbox

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize(name: str) -> str:
    return _UNSAFE_CHARS.sub("_", name)


def device_hint_from_tag_and_ext(source_tag: str, ext: str) -> str:
    if source_tag.startswith("filename_galaxy"):
        return "galaxy"
    if source_tag.startswith("filename_kakaotalk"):
        return "kakaotalk"
    if source_tag.startswith("filename_screenshot"):
        return "screenshot"
    if source_tag.startswith("filename_whatsapp"):
        return "whatsapp"
    if ext.lower() in (".heic", ".heif"):
        return "iphone"
    return "misc"


def _device_hint_for(record: PhotoRecord, resolution: DateResolution) -> str:
    if record.device_hint and record.device_hint != "misc":
        return record.device_hint
    return device_hint_from_tag_and_ext(resolution.source_tag, record.local_path.suffix)


def compute_dest_path(
    library_root: Path, capture_dt: datetime, device_hint: str, original_name: str
) -> Path:
    """library_root/YYYY/YYYY-MM-DD/HHMMSS_<device>_<stem>.<ext>, with the HHMMSS prefix
    putting photos from both devices into one true interleaved chronological order within
    a day. Collisions (same-second capture from two devices) get a deterministic _2, _3
    suffix rather than overwriting."""
    stem = _sanitize(Path(original_name).stem)
    ext = Path(original_name).suffix.lower()
    day_dir = library_root / f"{capture_dt.year:04d}" / capture_dt.strftime("%Y-%m-%d")
    time_prefix = capture_dt.strftime("%H%M%S")

    candidate = day_dir / f"{time_prefix}_{device_hint}_{stem}{ext}"
    if not candidate.exists():
        return candidate

    n = 2
    while True:
        candidate = day_dir / f"{time_prefix}_{device_hint}_{stem}_{n}{ext}"
        if not candidate.exists():
            return candidate
        n += 1


@dataclass
class PipelineEntry:
    record: PhotoRecord
    action: str  # "organized" | "review" | "duplicate"
    dest_path: Path | None
    resolution: DateResolution | None


@dataclass
class PipelineReport:
    entries: list[PipelineEntry] = field(default_factory=list)

    def count(self, action: str) -> int:
        return sum(1 for e in self.entries if e.action == action)


def _iter_source_records(
    config: Config, manifest: Manifest, drive_service, source: str
) -> Iterator[PhotoRecord]:
    if source in ("drive", "all") and drive_service is not None:
        yield from sync_all_sources(drive_service, config, manifest)
    if source in ("naver", "all"):
        yield from scan_inbox(config.naver_inbox_dir)


def run_pipeline(
    config: Config,
    manifest: Manifest,
    drive_service=None,
    source: str = "all",
    dry_run: bool = False,
) -> PipelineReport:
    """Drive sync -> Naver inbox scan -> hash -> dedup -> resolve date -> copy into
    library/ or _review/. Never deletes or modifies source files. In dry-run mode,
    Drive files still have to be downloaded to compute a hash and resolve an accurate
    date (there is no way to preview EXIF-based confidence without reading the file),
    but nothing is written to the manifest or copied into library/_review, so a dry run
    never changes on-disk state that a later real run would observe.
    """
    ensure_directories(config)
    report = PipelineReport()

    for record in _iter_source_records(config, manifest, drive_service, source):
        record.sha256 = sha256_file(record.local_path)

        existing = manifest.get_photo(record.sha256)
        if existing is not None:
            if not dry_run:
                register_source(manifest, record)
            dest = Path(existing["dest_path"]) if existing["dest_path"] else None
            report.entries.append(PipelineEntry(record, "duplicate", dest, None))
            continue

        resolution = resolve_date(record, config)
        device_hint = _device_hint_for(record, resolution)
        record.device_hint = device_hint
        size_bytes = record.local_path.stat().st_size

        auto_organize = (
            resolution.capture_dt is not None
            and resolution.confidence.rank >= config.min_confidence_for_auto_organize.rank
        )

        if auto_organize:
            dest = compute_dest_path(
                config.library_root, resolution.capture_dt, device_hint, record.original_name
            )
            status = "organized"
        else:
            dest = config.review_root / record.origin / _sanitize(record.original_name)
            status = "review"

        record.dest_path = dest
        record.resolution = resolution

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.local_path, dest)
            manifest.upsert_photo(
                record.sha256,
                str(dest),
                resolution.capture_dt,
                resolution.confidence.value,
                resolution.source_tag,
                status,
                size_bytes,
            )
            register_source(manifest, record)

        report.entries.append(
            PipelineEntry(record, "organized" if auto_organize else "review", dest, resolution)
        )

    return report
