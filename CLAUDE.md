# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository holds two local Python CLIs that together remove the photo bottleneck from
the owner's Naver Blog workflow, plus a checked-in MCP setup for Korean tax-law research:

- **`photo-organizer/`** — pulls photos backed up from two devices (Galaxy, iPhone) via two
  clouds (Google Drive, Naver Cloud) into one true chronological library.
- **`blog-assistant/`** — renders a blog draft plus its photos into a single self-contained
  preview page and a set of JPEGs numbered in insertion order.
- **`.mcp.json` + `mcp/`** — an MCP server giving Claude Code first-hand access to Korean
  statute text for tax research. Unrelated to the blog pipeline; it is here because a
  project-scoped `.mcp.json` is the one MCP config that travels with a clone.

The draft *writing* itself is not automated here: it runs through Claude Code on the owner's
PC using the prompt assets in `blog-assistant/prompts/`. There is deliberately no server and
no LLM API key anywhere in this repo — an earlier design that called an LLM from a serverless
function was dropped in favour of "write on the PC with Claude Code, render locally", which
costs nothing and lets Claude see the actual photos when choosing where each one goes.

End-to-end flow: upload photos to a Drive folder from the phone → `photo-organizer` syncs and
dates them → Claude Code writes the draft, naming photos inline as
`[이미지: 파일명 | 설명]` → `blog-assistant` renders the preview + numbered JPEGs → paste into
the Naver editor and insert photos in order.

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

The owner works on Windows. In PowerShell there is no `&&` (5.1) and no
`source .venv/bin/activate` — run one command per line and call
`.venv\Scripts\python.exe` directly instead of activating, which also sidesteps
the execution-policy block on `Activate.ps1`. Both READMEs carry the PowerShell
form of the install block.

`config.yaml` (gitignored) is copied from `config.example.yaml` and holds Drive folder IDs and
local paths — see `photo-organizer/README.md` for the full one-time setup (Google Cloud OAuth
client, folder IDs, local inbox/library paths).

## Commands (run from `blog-assistant/`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # Pillow, pillow-heif only
pip install -r requirements-dev.txt      # + pytest

pytest                                   # full test suite
pytest tests/test_image_slots.py         # a single test file
pytest tests/test_image_slots.py::test_missing_file_is_reported_not_guessed  # a single test

python render_post.py <draft.md> --photos <photo-dir> [--out-dir <dir>]
```

## Commands (MCP, run from the repo root)

```bash
claude mcp list                          # confirm the server connects
npm view korean-law-mcp version          # check for a newer korean-law-mcp to pin
```

`LAW_OC` (the 법제처 OPEN API key) must be set in the environment before `korean-law` will
answer — see `mcp/README.md` for how to get one and where to put it. Node.js 20+ required;
`npx` fetches the server itself, so there is nothing to install per machine.

## Architecture — photo-organizer

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

## Architecture — blog-assistant

`render_post.py` is the only entrypoint: draft markdown + a photo folder → one preview page and
a folder of numbered JPEGs.

- **Markdown** (`src/markdown_naver.py`): a deliberately narrow converter for exactly the syntax
  the blog-writer agent emits (`#` / `## ▶` / `==highlight==` / `> quote` / `**bold**` /
  `~~del~~` / `` `code` `` / `---`). Not a general markdown implementation — Naver strips most
  structural HTML, so every element carries inline styles, and predictability beats coverage.
  Each non-blank line becomes its own centred `<p>`, matching the mobile line-break rule in the
  format prompt. Image markers are replaced by `<!--IMAGE_SLOT:n-->` tokens that `page.py` later
  fills two different ways.
- **Photo matching** (`src/image_slots.py`): `[이미지: 파일명 | 설명]` slots are matched by
  filename first (case-insensitive, extension optional) and each match claims its photo; slots
  written without a filename are then filled from the *remaining* photos in capture-time order.
  A named file that is missing is never substituted with another photo — it becomes a visible
  warning, because silently swapping in the wrong photo is worse than leaving a hole.
- **Photos** (`src/photos.py`): EXIF-orientation-corrected via `ImageOps.exif_transpose` (phone
  photos otherwise render sideways), thumbnails inlined as base64 JPEG data URIs, and exports
  re-encoded to JPEG since the Naver editor does not reliably accept iPhone HEIC.
- **Page** (`src/page.py`): the preview and the clipboard payload are rendered from the same
  body but differ on purpose — the preview shows thumbnails in place, while the copied HTML
  carries visible `[사진 N]` markers, since Naver will not accept locally embedded images and
  the user has to insert them by hand. Unresolved slots copy as `[사진 없음]` so they can't be
  mistaken for a numbered file that exists. The whole page is self-contained (no external CSS,
  JS, fonts, or image URLs) so it can be dropped in Drive and opened on a phone.

## Architecture — tax-law MCP

`.mcp.json` registers one server, **`korean-law`** (`korean-law-mcp`, 법제처 국가법령정보센터
OPEN API): statute text — the 법률/시행령/시행규칙 of 국세기본법·소득세법·법인세법·
부가가치세법·조특법 — plus court precedents, administrative rules, and 18 decision domains
including 조세심판례. It reads the official 법제처 API, so for article text there is no more
accurate path.

Before writing a conclusion, run `legal_analysis(mode=verify_citations)`; a fabricated article
or case number is the failure mode that matters most here. The server is not official, so
nothing it returns is a substitute for the original text plus a 세무사 review.

The version is pinned (`korean-law-mcp@4.9.6`) because a legal database that silently changes
answers between runs is worse than one that needs a manual bump. `npx` fetches it, so a fresh
clone needs no install step. `LAW_OC` is read via `${LAW_OC}` expansion so the key stays out of
git — this repo still contains no committed credentials and no LLM API key.

Deliberately *not* registered: `taxlaw-nts-mcp`, which would add 국세청 해석례·기본통칙·홈택스
상담사례 (material the 법제처 API does not carry) but is a new unofficial client that scrapes
국세법령정보시스템 for want of a public API. `mcp/README.md` records what it would take to add
later, including the npm/TypeScript pitfalls already hit while trying it.

## Conventions

- Every module under `src/` is pure/testable except `drive_client.py` (network + OAuth) and the
  CLI entrypoint; `tests/` covers the rest without needing network access or real credentials.
- Directories holding real photos, credentials, or manifest state (`library/`, `_review/`,
  `state/`, `raw_cache/`, `credentials/`, `config.yaml`) live outside version control by design
  — only code and `config.example.yaml` are committed.
- Same rule for blog content: drafts, rendered previews, exported photos, and the owner's
  personal voice samples (`voice-samples.md`) are gitignored. Only the reusable prompt rules
  under `blog-assistant/prompts/` are committed — they were extracted from the owner's separate
  `everything-claude-code_jm` repo, deliberately leaving personal writing samples and published
  posts behind.
- Both tools are copy-only and read their sources without modifying them.
- The MCP setup follows the same split: `.mcp.json` and `.claude/settings.json` are committed so
  a fresh clone connects the same server at the same version, while the `LAW_OC` key stays
  local in the environment.
