from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.organizer import compute_dest_path, device_hint_from_tag_and_ext

_KST = ZoneInfo("Asia/Seoul")


def test_dest_path_matches_scheme(tmp_path):
    dt = datetime(2023, 12, 25, 14, 30, 22, tzinfo=_KST)
    dest = compute_dest_path(tmp_path, dt, "galaxy", "20231225_143022.jpg")
    assert dest == tmp_path / "2023" / "2023-12-25" / "143022_galaxy_20231225_143022.jpg"


def test_same_second_collision_gets_suffix(tmp_path):
    dt = datetime(2023, 12, 25, 14, 30, 22, tzinfo=_KST)

    first = compute_dest_path(tmp_path, dt, "galaxy", "photo.jpg")
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_bytes(b"one")

    second = compute_dest_path(tmp_path, dt, "galaxy", "photo.jpg")
    assert second != first
    assert second.name == "143022_galaxy_photo_2.jpg"

    second.write_bytes(b"two")
    third = compute_dest_path(tmp_path, dt, "galaxy", "photo.jpg")
    assert third.name == "143022_galaxy_photo_3.jpg"


def test_device_hint_inferred_from_source_tag_and_extension():
    assert device_hint_from_tag_and_ext("filename_galaxy", ".jpg") == "galaxy"
    assert device_hint_from_tag_and_ext("filename_kakaotalk", ".jpg") == "kakaotalk"
    assert device_hint_from_tag_and_ext("filename_screenshot_android", ".jpg") == "screenshot"
    assert device_hint_from_tag_and_ext("filename_whatsapp", ".jpg") == "whatsapp"
    assert device_hint_from_tag_and_ext("exif_datetimeoriginal", ".heic") == "iphone"
    assert device_hint_from_tag_and_ext("fs_mtime", ".jpg") == "misc"
