from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from dateutil import parser as dateutil_parser

from src.config import Config
from src.exif_utils import read_capture_datetime
from src.filename_patterns import build_custom_patterns, resolve_from_filename
from src.models import Confidence, DateResolution, PhotoRecord

_EXIF_LIKE_FORMAT = "%Y:%m:%d %H:%M:%S"


def _plausible(dt: datetime, min_valid_year: int, now_local_naive: datetime) -> bool:
    """Guards against corrupt EXIF/filenames: reject anything absurdly old or in the future."""
    if dt.year < min_valid_year:
        return False
    if dt > now_local_naive + timedelta(days=1):
        return False
    return True


def _parse_drive_image_time(raw: str) -> datetime | None:
    # Drive's imageMediaMetadata.time is documented as an EXIF-format timestamp, but be
    # lenient and fall back to general ISO parsing for any variant we encounter.
    try:
        return datetime.strptime(raw, _EXIF_LIKE_FORMAT)
    except ValueError:
        pass
    try:
        return dateutil_parser.isoparse(raw).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _parse_rfc3339_to_tz(raw: str, tz) -> datetime | None:
    try:
        parsed = dateutil_parser.isoparse(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_timezone.utc)
        return parsed.astimezone(tz)
    except (ValueError, TypeError):
        return None


def resolve_date(record: PhotoRecord, config: Config) -> DateResolution:
    """Priority chain: EXIF -> filename pattern -> Drive metadata -> fs mtime -> unresolved.

    All naive timestamps (EXIF, filenames, Drive imageMediaMetadata.time) are assumed to
    already represent local wall-clock time in config.timezone -- they carry no offset of
    their own. Drive's createdTime and filesystem mtime are true UTC instants and are
    converted into config.timezone instead of being reinterpreted as if they were already
    local. Every returned capture_dt is timezone-aware in config.timezone.
    """
    tz = config.timezone
    now_local_naive = datetime.now(tz).replace(tzinfo=None)

    # 1. EXIF
    exif_dt, exif_tag = read_capture_datetime(record.local_path)
    if exif_dt and _plausible(exif_dt, config.min_valid_year, now_local_naive):
        return DateResolution(
            capture_dt=exif_dt.replace(tzinfo=tz),
            confidence=Confidence.HIGH,
            source_tag=exif_tag,
            detail=f"EXIF tag {exif_tag}",
        )

    # 2. Filename pattern (a match with no date, e.g. default iPhone IMG_1234.HEIC, is a
    # deliberate short-circuit that falls through here without being treated as a match)
    custom_patterns = build_custom_patterns(config.custom_filename_patterns)
    match = resolve_from_filename(record.original_name, custom_patterns)
    if match and match.capture_dt and _plausible(
        match.capture_dt, config.min_valid_year, now_local_naive
    ):
        return DateResolution(
            capture_dt=match.capture_dt.replace(tzinfo=tz),
            confidence=Confidence.MEDIUM,
            source_tag=match.pattern_name,
            detail=f"filename pattern {match.pattern_name}",
        )

    # 3. Google Drive metadata (only present for Drive-sourced files)
    if record.drive_meta:
        if record.drive_meta.image_media_time:
            dt = _parse_drive_image_time(record.drive_meta.image_media_time)
            if dt and _plausible(dt, config.min_valid_year, now_local_naive):
                return DateResolution(
                    capture_dt=dt.replace(tzinfo=tz),
                    confidence=Confidence.LOW,
                    source_tag="drive_image_metadata",
                    detail="Drive imageMediaMetadata.time",
                )
        if record.drive_meta.created_time:
            dt = _parse_rfc3339_to_tz(record.drive_meta.created_time, tz)
            if dt and _plausible(dt.replace(tzinfo=None), config.min_valid_year, now_local_naive):
                return DateResolution(
                    capture_dt=dt,
                    confidence=Confidence.LOW,
                    source_tag="drive_created_time",
                    detail="Drive createdTime (upload time, not capture time)",
                )

    # 4. Filesystem mtime -- least trustworthy, downloads/copies often reset it
    try:
        mtime = record.local_path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime, tz=dt_timezone.utc).astimezone(tz)
        if _plausible(dt.replace(tzinfo=None), config.min_valid_year, now_local_naive):
            return DateResolution(
                capture_dt=dt,
                confidence=Confidence.VERY_LOW,
                source_tag="fs_mtime",
                detail="Filesystem modification time",
            )
    except OSError:
        pass

    # 5. Give up -- routed to _review/, never silently guessed
    return DateResolution(
        capture_dt=None,
        confidence=Confidence.NONE,
        source_tag="unresolved",
        detail="No EXIF, no recognized filename pattern, no usable fallback metadata",
    )
