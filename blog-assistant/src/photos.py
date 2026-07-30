"""Reading, ordering, and re-encoding the photo files a draft refers to."""

from __future__ import annotations

import base64
import io
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover - required dep, but degrade rather than crash
    pass

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif", ".webp"}

_EXIF_DATETIME_ORIGINAL = 36867
_EXIF_FORMAT = "%Y:%m:%d %H:%M:%S"

THUMBNAIL_MAX_WIDTH = 800
THUMBNAIL_QUALITY = 75
EXPORT_MAX_EDGE = 2048
EXPORT_QUALITY = 88


def capture_time(path: Path) -> datetime:
    """EXIF capture time when available, else file mtime. Used only to order photos, so a
    rough answer is fine -- photo-organizer already handles authoritative dating."""
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if exif:
                from PIL import ExifTags

                raw = exif.get_ifd(ExifTags.IFD.Exif).get(_EXIF_DATETIME_ORIGINAL)
                if isinstance(raw, str) and not raw.startswith("0000"):
                    try:
                        return datetime.strptime(raw.strip(), _EXIF_FORMAT)
                    except ValueError:
                        pass
    except Exception:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(tzinfo=None)


def list_photos(photo_dir: Path) -> list[Path]:
    """All images under photo_dir, in capture-time order (filename as tiebreaker).

    Note that photo-organizer's library already encodes capture time in the filename
    (HHMMSS_device_name.ext), so for those folders name order and capture order agree.
    """
    if not photo_dir.exists():
        return []
    candidates = [
        p
        for p in photo_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(candidates, key=lambda p: (capture_time(p), p.name))


def _load_upright(path: Path) -> Image.Image:
    img = Image.open(path)
    # Phone photos carry an orientation tag; without this they render sideways.
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def thumbnail_data_uri(path: Path, max_width: int = THUMBNAIL_MAX_WIDTH) -> str:
    """A base64 JPEG data URI, so the preview page stays a single self-contained file
    that can be dropped in Drive and opened on a phone."""
    with _load_upright(path) as img:
        if img.width > max_width:
            height = round(img.height * max_width / img.width)
            img = img.resize((max_width, height), Image.LANCZOS)
        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=THUMBNAIL_QUALITY)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def export_jpeg(path: Path, dest: Path, max_edge: int = EXPORT_MAX_EDGE) -> None:
    """Re-encode to JPEG for uploading. iPhone HEIC files are not reliably accepted by
    the Naver editor, and this also normalises orientation so photos upload upright."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _load_upright(path) as img:
        longest = max(img.width, img.height)
        if longest > max_edge:
            scale = max_edge / longest
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        img.convert("RGB").save(dest, format="JPEG", quality=EXPORT_QUALITY)
