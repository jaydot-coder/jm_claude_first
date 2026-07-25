from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from src.models import Confidence

_CONFIDENCE_BY_NAME = {c.value: c for c in Confidence}


@dataclass
class DriveSourceFolder:
    folder_id: str
    device_hint: str


@dataclass
class CustomPattern:
    name: str
    regex: str
    group: str
    format: str


@dataclass
class Config:
    timezone: ZoneInfo
    min_confidence_for_auto_organize: Confidence
    min_valid_year: int
    drive_source_folders: list[DriveSourceFolder]
    naver_inbox_dir: Path
    library_root: Path
    review_root: Path
    state_dir: Path
    raw_cache_dir: Path
    credentials_dir: Path
    custom_filename_patterns: list[CustomPattern] = field(default_factory=list)

    @property
    def manifest_path(self) -> Path:
        return self.state_dir / "manifest.sqlite3"

    @property
    def credentials_path(self) -> Path:
        return self.credentials_dir / "credentials.json"

    @property
    def token_path(self) -> Path:
        return self.credentials_dir / "token.json"

    @property
    def review_manifest_csv(self) -> Path:
        return self.review_root / "review_manifest.csv"


def _expand(path_str: str) -> Path:
    return Path(path_str).expanduser().resolve()


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. Copy config.example.yaml to config.yaml first."
        )
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    required = [
        "naver_inbox_dir",
        "library_root",
        "review_root",
        "state_dir",
        "raw_cache_dir",
        "credentials_dir",
    ]
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"Config is missing required keys: {', '.join(missing)}")

    confidence_name = raw.get("min_confidence_for_auto_organize", "medium")
    if confidence_name not in _CONFIDENCE_BY_NAME:
        raise ValueError(
            f"Invalid min_confidence_for_auto_organize: {confidence_name!r}. "
            f"Must be one of {list(_CONFIDENCE_BY_NAME)}."
        )

    drive_folders = [
        DriveSourceFolder(folder_id=f["folder_id"], device_hint=f.get("device_hint", "misc"))
        for f in raw.get("drive_source_folders", [])
        if f.get("folder_id") and not str(f.get("folder_id")).startswith("REPLACE_WITH")
    ]

    custom_patterns = [
        CustomPattern(
            name=p["name"], regex=p["regex"], group=p["group"], format=p["format"]
        )
        for p in raw.get("custom_filename_patterns") or []
    ]

    return Config(
        timezone=ZoneInfo(raw.get("timezone", "Asia/Seoul")),
        min_confidence_for_auto_organize=_CONFIDENCE_BY_NAME[confidence_name],
        min_valid_year=int(raw.get("min_valid_year", 2000)),
        drive_source_folders=drive_folders,
        naver_inbox_dir=_expand(raw["naver_inbox_dir"]),
        library_root=_expand(raw["library_root"]),
        review_root=_expand(raw["review_root"]),
        state_dir=_expand(raw["state_dir"]),
        raw_cache_dir=_expand(raw["raw_cache_dir"]),
        credentials_dir=_expand(raw["credentials_dir"]),
        custom_filename_patterns=custom_patterns,
    )


def ensure_directories(config: Config) -> None:
    for d in (
        config.naver_inbox_dir,
        config.library_root,
        config.review_root,
        config.state_dir,
        config.raw_cache_dir,
        config.credentials_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)
