from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.dateresolve import resolve_date
from src.models import Confidence, DriveFileMeta, PhotoRecord


def test_exif_wins_over_everything_else(make_jpeg, base_config):
    path = make_jpeg("IMG_20200101_000000.jpg", datetime_original="2023:12:25 14:30:22")
    record = PhotoRecord(local_path=path, origin="naver_inbox", original_name=path.name, origin_path_or_id=str(path))
    resolution = resolve_date(record, base_config)
    assert resolution.confidence == Confidence.HIGH
    assert resolution.source_tag == "exif_datetimeoriginal"
    assert resolution.capture_dt.replace(tzinfo=None) == datetime(2023, 12, 25, 14, 30, 22)


def test_falls_back_to_filename_when_no_exif(make_jpeg, base_config):
    path = make_jpeg("20231225_143022.jpg")
    record = PhotoRecord(local_path=path, origin="naver_inbox", original_name=path.name, origin_path_or_id=str(path))
    resolution = resolve_date(record, base_config)
    assert resolution.confidence == Confidence.MEDIUM
    assert resolution.source_tag == "filename_galaxy"
    assert resolution.capture_dt.replace(tzinfo=None) == datetime(2023, 12, 25, 14, 30, 22)


def test_falls_back_to_drive_metadata_when_no_exif_or_filename_match(make_jpeg, base_config):
    path = make_jpeg("IMG_9999.jpg")  # no EXIF, filename does not match any built-in pattern
    drive_meta = DriveFileMeta(
        file_id="abc123",
        name=path.name,
        md5_checksum=None,
        created_time="2022-05-01T01:00:00.000Z",
        image_media_time="2022:05:01 10:00:00",
        device_hint="galaxy",
    )
    record = PhotoRecord(
        local_path=path,
        origin="drive",
        original_name=path.name,
        origin_path_or_id="abc123",
        drive_meta=drive_meta,
    )
    resolution = resolve_date(record, base_config)
    assert resolution.confidence == Confidence.LOW
    assert resolution.source_tag == "drive_image_metadata"
    assert resolution.capture_dt.replace(tzinfo=None) == datetime(2022, 5, 1, 10, 0, 0)


def test_falls_back_to_filesystem_mtime_as_last_resort(make_jpeg, base_config):
    path = make_jpeg("IMG_9999.jpg")
    target_utc = datetime(2022, 3, 1, 3, 0, 0, tzinfo=timezone.utc)  # 12:00 KST
    epoch = target_utc.timestamp()
    os.utime(path, (epoch, epoch))

    record = PhotoRecord(local_path=path, origin="naver_inbox", original_name=path.name, origin_path_or_id=str(path))
    resolution = resolve_date(record, base_config)

    assert resolution.confidence == Confidence.VERY_LOW
    assert resolution.source_tag == "fs_mtime"
    assert resolution.capture_dt == target_utc.astimezone(ZoneInfo("Asia/Seoul"))


def test_completely_unresolvable_photo_is_flagged_for_review(make_jpeg, base_config):
    path = make_jpeg("IMG_9999.jpg", datetime_original="2099:01:01 00:00:00")  # implausible future
    old_epoch = datetime(1990, 1, 1, tzinfo=timezone.utc).timestamp()  # before min_valid_year
    os.utime(path, (old_epoch, old_epoch))

    record = PhotoRecord(local_path=path, origin="naver_inbox", original_name=path.name, origin_path_or_id=str(path))
    resolution = resolve_date(record, base_config)

    assert resolution.confidence == Confidence.NONE
    assert resolution.source_tag == "unresolved"
    assert resolution.capture_dt is None
