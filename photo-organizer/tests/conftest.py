from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from PIL import ExifTags, Image

from src.config import Config
from src.models import Confidence


def _make_exif(datetime_original: str | None = None, datetime_tag: str | None = None):
    img = Image.new("RGB", (4, 4), color="red")
    exif = img.getexif()
    if datetime_tag:
        exif[306] = datetime_tag  # top-level IFD0 DateTime
    if datetime_original:
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        exif_ifd[36867] = datetime_original  # DateTimeOriginal, in the Exif sub-IFD
    return img, exif


@pytest.fixture
def make_jpeg(tmp_path):
    def _make(
        name: str,
        datetime_original: str | None = None,
        datetime_tag: str | None = None,
    ) -> Path:
        img, exif = _make_exif(datetime_original, datetime_tag)
        path = tmp_path / name
        if datetime_original or datetime_tag:
            img.save(path, exif=exif)
        else:
            img.save(path)
        return path

    return _make


@pytest.fixture
def make_png(tmp_path):
    def _make(name: str) -> Path:
        path = tmp_path / name
        Image.new("RGB", (4, 4), color="blue").save(path)
        return path

    return _make


@pytest.fixture
def base_config(tmp_path) -> Config:
    return Config(
        timezone=ZoneInfo("Asia/Seoul"),
        min_confidence_for_auto_organize=Confidence.MEDIUM,
        min_valid_year=2000,
        drive_source_folders=[],
        naver_inbox_dir=tmp_path / "naver_inbox",
        library_root=tmp_path / "library",
        review_root=tmp_path / "review",
        state_dir=tmp_path / "state",
        raw_cache_dir=tmp_path / "raw_cache",
        credentials_dir=tmp_path / "credentials",
    )
