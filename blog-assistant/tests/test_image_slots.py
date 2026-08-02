from __future__ import annotations

from pathlib import Path

import pytest

from src.image_slots import parse_slot_body, resolve_slots


@pytest.mark.parametrize(
    "body,expected",
    [
        ("a.jpg | 기차역 플랫폼", ("a.jpg", "기차역 플랫폼")),
        ("  a.jpg  |  플랫폼  ", ("a.jpg", "플랫폼")),
        ("숙소 내부", (None, "숙소 내부")),
        ("IMG_1234.HEIC", ("IMG_1234.HEIC", "")),  # filename with no caption
        ("a.jpg |", ("a.jpg", "")),
    ],
)
def test_parse_slot_body(body, expected):
    assert parse_slot_body(body) == expected


def _photos(tmp_path: Path, *names: str) -> list[Path]:
    paths = []
    for i, name in enumerate(names):
        p = tmp_path / name
        p.write_bytes(b"x")
        # Distinct mtimes so capture-time ordering is deterministic.
        import os

        os.utime(p, (1700000000 + i * 60, 1700000000 + i * 60))
        paths.append(p)
    return paths


def test_explicit_filenames_are_matched(tmp_path):
    photos = _photos(tmp_path, "one.jpg", "two.jpg")
    resolution = resolve_slots(["two.jpg | 둘째", "one.jpg | 첫째"], photos)
    assert [s.photo.name for s in resolution.slots] == ["two.jpg", "one.jpg"]
    assert resolution.unused_photos == []


def test_filename_match_is_case_insensitive_and_stem_tolerant(tmp_path):
    photos = _photos(tmp_path, "IMG_1234.JPG")
    resolution = resolve_slots(["img_1234.jpg | 설명"], photos)
    assert resolution.slots[0].photo == photos[0]

    resolution = resolve_slots(["IMG_1234 | 확장자 없이"], photos)
    assert resolution.slots[0].photo == photos[0]


def test_missing_file_is_reported_not_guessed(tmp_path):
    photos = _photos(tmp_path, "one.jpg")
    resolution = resolve_slots(["nope.jpg | 설명"], photos)
    assert resolution.slots[0].photo is None
    assert "nope.jpg" in resolution.slots[0].problem
    # The available photo must not be silently substituted for the missing one.
    assert resolution.unused_photos == [photos[0]]


def test_same_photo_used_twice_is_flagged(tmp_path):
    photos = _photos(tmp_path, "one.jpg")
    resolution = resolve_slots(["one.jpg | 처음", "one.jpg | 또"], photos)
    assert resolution.slots[0].photo == photos[0]
    assert resolution.slots[1].photo is None
    assert "이미 사용" in resolution.slots[1].problem


def test_unnamed_slots_fill_from_remaining_in_capture_order(tmp_path):
    photos = _photos(tmp_path, "a.jpg", "b.jpg", "c.jpg")
    # Middle photo is claimed by name; unnamed slots take the rest oldest-first.
    resolution = resolve_slots(["설명1", "b.jpg | 지정", "설명2"], photos)
    assert resolution.slots[0].photo.name == "a.jpg"
    assert resolution.slots[1].photo.name == "b.jpg"
    assert resolution.slots[2].photo.name == "c.jpg"
    assert resolution.unused_photos == []


def test_running_out_of_photos_is_flagged(tmp_path):
    photos = _photos(tmp_path, "a.jpg")
    resolution = resolve_slots(["설명1", "설명2"], photos)
    assert resolution.slots[0].photo.name == "a.jpg"
    assert resolution.slots[1].photo is None
    assert "부족" in resolution.slots[1].problem


def test_unused_photos_are_listed(tmp_path):
    photos = _photos(tmp_path, "a.jpg", "b.jpg")
    resolution = resolve_slots(["a.jpg | 하나만"], photos)
    assert [p.name for p in resolution.unused_photos] == ["b.jpg"]


def test_slot_numbers_are_one_based(tmp_path):
    photos = _photos(tmp_path, "a.jpg")
    resolution = resolve_slots(["a.jpg | x"], photos)
    assert resolution.slots[0].number == 1
