from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterator

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.config import Config, DriveSourceFolder
from src.hashing import md5_file
from src.models import DriveFileMeta, PhotoRecord

log = logging.getLogger(__name__)

# Read-only on purpose: this tool must never be able to modify or delete anything in the
# user's Drive, even by accident. drive_client.py must only ever call .list() / .get_media().
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_LIST_FIELDS = (
    "nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, "
    "imageMediaMetadata, md5Checksum)"
)
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    return _UNSAFE_CHARS.sub("_", name)


def get_credentials(config: Config) -> Credentials:
    creds: Credentials | None = None
    if config.token_path.exists():
        creds = Credentials.from_authorized_user_file(str(config.token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not config.credentials_path.exists():
            raise FileNotFoundError(
                f"Missing OAuth client secret at {config.credentials_path}. "
                "Create one in Google Cloud Console (Desktop app) and save it there."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(config.credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)

    config.credentials_dir.mkdir(parents=True, exist_ok=True)
    config.token_path.write_text(creds.to_json())
    return creds


def build_drive_service(config: Config):
    creds = get_credentials(config)
    return build("drive", "v3", credentials=creds)


def list_image_files(service, folder_id: str) -> Iterator[dict]:
    query = f"'{folder_id}' in parents and trashed = false and mimeType contains 'image/'"
    page_token = None
    while True:
        response = (
            service.files()
            .list(q=query, fields=_LIST_FIELDS, pageSize=1000, pageToken=page_token)
            .execute()
        )
        yield from response.get("files", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def download_file(service, file_id: str, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def sync_source_folder(
    service, source: DriveSourceFolder, config: Config, manifest
) -> Iterator[PhotoRecord]:
    """Yields a PhotoRecord for every file that is new or changed since the last sync
    (diffed against manifest.drive_sync_state by file_id + md5Checksum), downloading it
    into raw_cache_dir/drive/ first. Unchanged files are skipped without downloading."""
    for f in list_image_files(service, source.folder_id):
        file_id = f["id"]
        md5 = f.get("md5Checksum")
        existing = manifest.get_drive_sync_state(file_id)
        cached_path = Path(existing["local_cache_path"]) if existing and existing["local_cache_path"] else None
        if existing and existing["md5_checksum"] == md5 and cached_path and cached_path.exists():
            continue

        dest = config.raw_cache_dir / "drive" / f"{file_id}_{_sanitize_filename(f['name'])}"
        download_file(service, file_id, dest)

        if md5:
            local_md5 = md5_file(dest)
            if local_md5 != md5:
                log.warning(
                    "Drive download integrity mismatch for %s (%s): expected md5 %s, got %s",
                    f["name"],
                    file_id,
                    md5,
                    local_md5,
                )

        manifest.upsert_drive_sync_state(file_id, f["name"], md5, str(dest))

        drive_meta = DriveFileMeta(
            file_id=file_id,
            name=f["name"],
            md5_checksum=md5,
            created_time=f.get("createdTime"),
            image_media_time=(f.get("imageMediaMetadata") or {}).get("time"),
            device_hint=source.device_hint,
        )
        yield PhotoRecord(
            local_path=dest,
            origin="drive",
            original_name=f["name"],
            origin_path_or_id=file_id,
            device_hint=source.device_hint,
            drive_meta=drive_meta,
        )


def sync_all_sources(service, config: Config, manifest) -> Iterator[PhotoRecord]:
    for source in config.drive_source_folders:
        yield from sync_source_folder(service, source, config, manifest)
