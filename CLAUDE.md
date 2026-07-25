# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository hosts `photo-organizer/`, a local Python CLI that organizes photos backed up
from two devices (Galaxy, iPhone) via two clouds (Google Drive, Naver Cloud) into one true
chronological library, to unblock a Naver Blog semi-automation workflow that this repo does
**not** contain. There is no other code in the repo yet.

## Commands (run from `photo-organizer/`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # runtime deps
pip install -r requirements-dev.txt      # + pytest, freezegun

pytest                                   # full test suite (pure logic, no network/creds)
pytest tests/test_dateresolve.py         # a single test file
pytest tests/test_dateresolve.py::test_exif_wins_over_everything_else  # a single test

python organize_photos.py auth --config config.yaml   # one-time Google OAuth handshake
python organize_photos.py run --config config.yaml --dry-run   # preview, writes nothing
python organize_photos.py run --config config.yaml             # organize for real
python organize_photos.py review list --config config.yaml
python organize_photos.py status --config config.yaml
```

`config.yaml` (gitignored) is copied from `config.example.yaml` and holds Drive folder IDs and
local paths — see `photo-organizer/README.md` for the full one-time setup (Google Cloud OAuth
client, folder IDs, local inbox/library paths).

## Architecture

The pipeline (orchestrated by `src/organizer.py:run_pipeline`) is: pull photos from two sources
→ hash → dedup → resolve a capture date → copy into a dated library, or into a review area if
the date can't be trusted.

- **Sources** (`src/drive_client.py`, `src/naver_inbox.py`): Google Drive is synced via a
  read-only OAuth app (`drive.readonly` scope only — the client only ever calls `.list()` /
  `.get_media()`, never a write/delete endpoint), diffed incrementally against
  `drive_sync_state` in the manifest so unchanged files aren't re-downloaded. Naver Cloud has no
  usable API, so its "source" is just a local folder (`naver_inbox_dir`) the user manually drops
  downloads into; `naver_inbox.py` recursively scans it.
- **Date resolution** (`src/dateresolve.py`, the core of the tool): a priority chain — EXIF
  (`src/exif_utils.py`, HEIC-aware via `pillow-heif`) → filename pattern (`src/filename_patterns.py`,
  regex library for Galaxy/KakaoTalk/screenshot/WhatsApp conventions, extensible via
  `custom_filename_patterns` in config) → Drive file metadata (Drive-sourced files only) →
  filesystem mtime → give up. Every result carries a `Confidence` tier; only
  `min_confidence_for_auto_organize`-or-above results get auto-filed, everything else goes to
  `_review/` rather than being silently mis-sorted. All naive timestamps are interpreted in
  `config.timezone` (default `Asia/Seoul`) before any date-folder bucketing happens.
- **Identity & idempotency** (`src/manifest.py`, `src/dedup.py`): a SQLite manifest
  (`photos`, `photo_sources`, `drive_sync_state` tables) keyed by sha256 content hash. The same
  photo backed up to both clouds is organized exactly once; re-running the tool only processes
  genuinely new files.
- **Output** (`src/organizer.py:compute_dest_path`): `library/YYYY/YYYY-MM-DD/HHMMSS_<device>_<name>.<ext>`.
  The `HHMMSS` prefix is what makes photos from both devices interleave in true chronological
  order within a day, regardless of which device or cloud they came from. Same-second collisions
  get a deterministic `_2`, `_3` suffix. Low-confidence files land in `_review/<source>/` under
  their original filename (never renamed on a guess) plus a regenerated `review_manifest.csv`;
  `src/review.py:resolve_review_item` lets a human manually confirm a date and promote one into
  the library.
- **Safety**: default action is always copy, never move/delete — Drive's read-only scope makes
  this structurally true on that side, and the Naver inbox folder is only ever read. `--dry-run`
  runs the full resolution pipeline (including real Drive downloads, since EXIF-based confidence
  can't be previewed without reading the file) but skips all manifest and library/review writes.
- **CLI** (`organize_photos.py`): `run` (default) / `review list` / `review resolve` / `status` /
  `auth` subcommands; `--config`/`-v` work before or after the subcommand.

## Conventions

- Every module under `src/` is pure/testable except `drive_client.py` (network + OAuth) and the
  CLI entrypoint; `tests/` covers the rest without needing network access or real credentials.
- Directories holding real photos, credentials, or manifest state (`library/`, `_review/`,
  `state/`, `raw_cache/`, `credentials/`, `config.yaml`) live outside version control by design
  — only code and `config.example.yaml` are committed.
