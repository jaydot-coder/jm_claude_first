from __future__ import annotations

from pathlib import Path

from src.config import ensure_directories
from src.dedup import is_duplicate, register_source
from src.manifest import Manifest
from src.models import PhotoRecord
from src.organizer import run_pipeline


def test_is_duplicate_reflects_manifest_state(tmp_path):
    manifest = Manifest(tmp_path / "manifest.sqlite3")
    try:
        assert not is_duplicate(manifest, "deadbeef")
        manifest.upsert_photo(
            "deadbeef", "/library/x.jpg", None, "high", "exif_datetimeoriginal", "organized", 100
        )
        assert is_duplicate(manifest, "deadbeef")
    finally:
        manifest.close()


def test_register_source_is_idempotent(tmp_path):
    manifest = Manifest(tmp_path / "manifest.sqlite3")
    try:
        manifest.upsert_photo(
            "deadbeef", "/library/x.jpg", None, "high", "exif_datetimeoriginal", "organized", 100
        )
        record = PhotoRecord(
            local_path=Path("/tmp/a.jpg"),
            origin="naver_inbox",
            original_name="a.jpg",
            origin_path_or_id="/tmp/a.jpg",
            sha256="deadbeef",
        )
        register_source(manifest, record)
        register_source(manifest, record)  # repeat call must not raise or double-insert
        assert len(manifest.sources_for("deadbeef")) == 1
    finally:
        manifest.close()


def test_duplicate_content_across_sources_is_organized_once_and_idempotent(make_jpeg, base_config):
    ensure_directories(base_config)
    src_path = make_jpeg("20231225_143022.jpg")
    content = src_path.read_bytes()

    inbox = base_config.naver_inbox_dir
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "20231225_143022.jpg").write_bytes(content)
    (inbox / "copy_of_same_photo.jpg").write_bytes(content)  # identical bytes, different name

    manifest = Manifest(base_config.manifest_path)
    try:
        report = run_pipeline(base_config, manifest, drive_service=None, source="naver", dry_run=False)
        assert report.count("organized") == 1
        assert report.count("duplicate") == 1
        assert len(list(base_config.library_root.rglob("*.jpg"))) == 1

        # Re-running is idempotent: nothing new gets copied, both are now duplicates.
        report2 = run_pipeline(base_config, manifest, drive_service=None, source="naver", dry_run=False)
        assert report2.count("organized") == 0
        assert report2.count("duplicate") == 2
        assert len(list(base_config.library_root.rglob("*.jpg"))) == 1
    finally:
        manifest.close()
