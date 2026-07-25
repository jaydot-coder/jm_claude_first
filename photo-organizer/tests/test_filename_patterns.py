from __future__ import annotations

from datetime import datetime

import pytest

from src.filename_patterns import resolve_from_filename


@pytest.mark.parametrize(
    "filename,expected_pattern,expected_dt",
    [
        ("20231225_143022.jpg", "filename_galaxy", datetime(2023, 12, 25, 14, 30, 22)),
        ("IMG_20231225_143022.jpg", "filename_galaxy", datetime(2023, 12, 25, 14, 30, 22)),
        (
            "Screenshot_20231225-143022_KakaoTalk.jpg",
            "filename_screenshot_android",
            datetime(2023, 12, 25, 14, 30, 22),
        ),
        (
            "2023-12-25 14.30.22.png",
            "filename_screenshot_ios",
            datetime(2023, 12, 25, 14, 30, 22),
        ),
        (
            "Kakaotalk_20231225_143022123.jpg",
            "filename_kakaotalk",
            datetime(2023, 12, 25, 14, 30, 22),
        ),
        (
            "KakaoTalk_20231225_143022_003.jpg",
            "filename_kakaotalk",
            datetime(2023, 12, 25, 14, 30, 22),
        ),
        ("IMG-20231225-WA0001.jpg", "filename_whatsapp", datetime(2023, 12, 25, 0, 0, 0)),
    ],
)
def test_known_patterns_parse_correct_datetime(filename, expected_pattern, expected_dt):
    match = resolve_from_filename(filename)
    assert match is not None
    assert match.pattern_name == expected_pattern
    assert match.capture_dt == expected_dt


def test_iphone_default_name_recognized_but_no_date():
    match = resolve_from_filename("IMG_1234.HEIC")
    assert match is not None
    assert match.pattern_name == "filename_iphone_default_no_date"
    assert match.capture_dt is None


def test_completely_unrecognized_filename_returns_none():
    assert resolve_from_filename("random_export_file.jpg") is None


def test_custom_pattern_is_used():
    from src.config import CustomPattern
    from src.filename_patterns import build_custom_patterns

    custom = build_custom_patterns(
        [CustomPattern(name="my_camera", regex=r"^MYCAM_(?P<ts>\d{8}_\d{6})", group="ts", format="%Y%m%d_%H%M%S")]
    )
    match = resolve_from_filename("MYCAM_20231225_143022.jpg", custom)
    assert match is not None
    assert match.pattern_name == "my_camera"
    assert match.capture_dt == datetime(2023, 12, 25, 14, 30, 22)
