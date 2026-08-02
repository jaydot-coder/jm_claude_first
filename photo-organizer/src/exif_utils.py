from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover - pillow-heif is a required dep, but degrade gracefully
    pass

_EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"

# Tag IDs, in the order we trust them.
_DATETIME_ORIGINAL = 36867  # lives in the Exif sub-IFD
_DATETIME_DIGITIZED = 36868  # lives in the Exif sub-IFD
_DATETIME = 306  # lives in the top-level IFD0


def _parse_exif_dt(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or value.startswith("0000"):
        return None
    try:
        return datetime.strptime(value, _EXIF_DATETIME_FORMAT)
    except ValueError:
        return None


def read_capture_datetime(path: Path) -> tuple[datetime | None, str]:
    """Best-effort EXIF capture time. Returns (datetime_or_none, tag_used)."""
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if exif is None:
                return None, ""

            # DateTimeOriginal / DateTimeDigitized live in the Exif sub-IFD, not the
            # top-level IFD0 -- getexif() alone does not surface them.
            exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)

            dt = _parse_exif_dt(exif_ifd.get(_DATETIME_ORIGINAL))
            if dt:
                return dt, "exif_datetimeoriginal"

            dt = _parse_exif_dt(exif_ifd.get(_DATETIME_DIGITIZED))
            if dt:
                return dt, "exif_datetimedigitized"

            dt = _parse_exif_dt(exif.get(_DATETIME))
            if dt:
                return dt, "exif_datetime"

            return None, ""
    except Exception:
        # Corrupt/unsupported image, unreadable EXIF, etc. -- treat as "no EXIF".
        return None, ""
