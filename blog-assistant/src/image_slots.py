"""Matching `[이미지: ...]` markers in a draft to actual photo files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.photos import IMAGE_EXTENSIONS


@dataclass
class ImageSlot:
    index: int  # 0-based position among the draft's image markers
    raw: str
    requested_filename: str | None
    caption: str
    photo: Path | None = None
    problem: str | None = None

    @property
    def number(self) -> int:
        """1-based, matching the "사진 N" labels shown to the user."""
        return self.index + 1


@dataclass
class SlotResolution:
    slots: list[ImageSlot] = field(default_factory=list)
    unused_photos: list[Path] = field(default_factory=list)

    @property
    def filled(self) -> list[ImageSlot]:
        return [s for s in self.slots if s.photo is not None]

    @property
    def problems(self) -> list[ImageSlot]:
        return [s for s in self.slots if s.problem]


def parse_slot_body(body: str) -> tuple[str | None, str]:
    """`파일명 | 설명` -> (filename, caption); `설명` -> (None, caption).

    A body with no separator that still looks like a filename is treated as one, so a
    draft that names a photo without adding a caption still resolves.
    """
    if "|" in body:
        filename, _, caption = body.partition("|")
        return filename.strip() or None, caption.strip()

    stripped = body.strip()
    if Path(stripped).suffix.lower() in IMAGE_EXTENSIONS:
        return stripped, ""
    return None, stripped


def _build_lookup(photos: list[Path]) -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    for photo in photos:
        # Later duplicates must not shadow earlier ones, hence setdefault.
        lookup.setdefault(photo.name, photo)
        lookup.setdefault(photo.name.lower(), photo)
        lookup.setdefault(photo.stem.lower(), photo)
    return lookup


def resolve_slots(slot_bodies: list[str], photos: list[Path]) -> SlotResolution:
    """Explicitly named photos are matched first and claimed; any slot left without a
    name is then filled from the remaining photos in capture-time order."""
    lookup = _build_lookup(photos)
    slots = [
        ImageSlot(index=i, raw=body, requested_filename=name, caption=caption)
        for i, body in enumerate(slot_bodies)
        for name, caption in [parse_slot_body(body)]
    ]

    claimed: set[Path] = set()

    for slot in slots:
        if not slot.requested_filename:
            continue
        name = slot.requested_filename
        photo = lookup.get(name) or lookup.get(name.lower()) or lookup.get(Path(name).stem.lower())
        if photo is None:
            slot.problem = f"사진 폴더에 '{name}' 파일이 없습니다"
            continue
        if photo in claimed:
            slot.problem = f"'{photo.name}' 이 앞에서 이미 사용됐습니다"
            continue
        slot.photo = photo
        claimed.add(photo)

    remaining = [p for p in photos if p not in claimed]
    fallback = iter(remaining)
    for slot in slots:
        if slot.photo is not None or slot.requested_filename:
            continue
        photo = next(fallback, None)
        if photo is None:
            slot.problem = "배치할 사진이 부족합니다 (파일명 미지정 자리)"
            continue
        slot.photo = photo
        claimed.add(photo)

    return SlotResolution(
        slots=slots, unused_photos=[p for p in photos if p not in claimed]
    )
