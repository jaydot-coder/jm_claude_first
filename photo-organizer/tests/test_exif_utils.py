from __future__ import annotations

from datetime import datetime

from src.exif_utils import read_capture_datetime


def test_datetime_original_is_preferred(make_jpeg):
    path = make_jpeg(
        "with_original.jpg",
        datetime_original="2023:12:25 14:30:22",
        datetime_tag="2020:01:01 00:00:00",
    )
    dt, tag = read_capture_datetime(path)
    assert dt == datetime(2023, 12, 25, 14, 30, 22)
    assert tag == "exif_datetimeoriginal"


def test_falls_back_to_top_level_datetime(make_jpeg):
    path = make_jpeg("only_datetime.jpg", datetime_tag="2021:06:15 09:00:00")
    dt, tag = read_capture_datetime(path)
    assert dt == datetime(2021, 6, 15, 9, 0, 0)
    assert tag == "exif_datetime"


def test_png_has_no_exif(make_png):
    path = make_png("screenshot.png")
    dt, tag = read_capture_datetime(path)
    assert dt is None
    assert tag == ""


def test_jpeg_without_exif_returns_none(make_jpeg):
    path = make_jpeg("no_exif.jpg")
    dt, tag = read_capture_datetime(path)
    assert dt is None
    assert tag == ""


def test_corrupt_file_does_not_raise(tmp_path):
    # A file with a .heic extension but garbage bytes -- must degrade gracefully rather
    # than raising, since real HEIC decode failures should never crash the pipeline.
    path = tmp_path / "corrupt.heic"
    path.write_bytes(b"not a real image")
    dt, tag = read_capture_datetime(path)
    assert dt is None
    assert tag == ""
