from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.manifest import Manifest
from src.organizer import compute_dest_path, device_hint_from_tag_and_ext


def write_review_manifest_csv(config: Config, manifest: Manifest) -> Path:
    """Regenerated from the manifest's current review rows every call -- always reflects
    the true outstanding set rather than an append-only log that could go stale."""
    rows = manifest.list_by_status("review")
    config.review_root.mkdir(parents=True, exist_ok=True)
    csv_path = config.review_manifest_csv

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "sha256",
                "origin",
                "original_path_or_id",
                "best_guess_date",
                "confidence",
                "source_tag",
                "reviewed_copy_path",
            ]
        )
        for row in rows:
            sources = manifest.sources_for(row["sha256"])
            origin = sources[0]["origin"] if sources else ""
            origin_ref = sources[0]["origin_path_or_id"] if sources else ""
            writer.writerow(
                [
                    row["sha256"],
                    origin,
                    origin_ref,
                    row["capture_dt"] or "",
                    row["confidence"],
                    row["source_tag"],
                    row["dest_path"] or "",
                ]
            )
    return csv_path


def resolve_review_item(
    config: Config, manifest: Manifest, sha256: str, manual_date: datetime
) -> Path:
    """Manually confirm a capture date for a reviewed photo and promote it into library/."""
    row = manifest.get_photo(sha256)
    if row is None or row["status"] != "review":
        raise ValueError(f"No review-pending photo with sha256={sha256}")

    review_copy = Path(row["dest_path"]) if row["dest_path"] else None
    if review_copy is None or not review_copy.exists():
        raise FileNotFoundError(f"Review copy missing on disk for sha256={sha256}: {review_copy}")

    capture_dt = manual_date if manual_date.tzinfo else manual_date.replace(tzinfo=config.timezone)
    device_hint = device_hint_from_tag_and_ext(row["source_tag"], review_copy.suffix)

    dest = compute_dest_path(config.library_root, capture_dt, device_hint, review_copy.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(review_copy, dest)

    manifest.upsert_photo(
        sha256,
        str(dest),
        capture_dt,
        "high",
        "manual",
        "organized",
        review_copy.stat().st_size,
    )

    try:
        review_copy.unlink()
    except OSError:
        pass

    return dest
