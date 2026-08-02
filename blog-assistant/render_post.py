#!/usr/bin/env python3
"""Renders a blog draft plus its photos into one portable preview page.

    python render_post.py output/스페인여행_12일차.md --photos ~/naver-blog-photos/library/2025/2025-05-12
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from src.image_slots import resolve_slots
from src.markdown_naver import convert
from src.page import build_page
from src.photos import export_jpeg, list_photos

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_CAPTION_MAX = 40


def _slug(caption: str) -> str:
    cleaned = _UNSAFE.sub("", caption).strip().replace(" ", "_")
    return cleaned[:_CAPTION_MAX] or "photo"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="render_post.py")
    parser.add_argument("draft", help="Markdown draft written by the blog-writer agent")
    parser.add_argument(
        "--photos", required=True, help="Folder holding the photos the draft refers to"
    )
    parser.add_argument(
        "--out-dir", help="Where to write the preview page (default: alongside the draft)"
    )
    args = parser.parse_args(argv)

    draft_path = Path(args.draft).expanduser()
    if not draft_path.exists():
        print(f"초안 파일이 없습니다: {draft_path}", file=sys.stderr)
        return 1

    photo_dir = Path(args.photos).expanduser()
    if not photo_dir.exists():
        print(f"사진 폴더가 없습니다: {photo_dir}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else draft_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    converted = convert(draft_path.read_text(encoding="utf-8"))
    photos = list_photos(photo_dir)
    resolution = resolve_slots(converted.slot_bodies, photos)

    stem = draft_path.stem
    images_dir = out_dir / f"{stem}_images"
    exported: dict[int, str] = {}
    for slot in resolution.slots:
        if slot.photo is None:
            continue
        name = f"{slot.number:02d}_{_slug(slot.caption or slot.photo.stem)}.jpg"
        export_jpeg(slot.photo, images_dir / name)
        exported[slot.index] = name

    page_html = build_page(converted, resolution, exported, stem)
    page_path = out_dir / f"{stem}_preview.html"
    page_path.write_text(page_html, encoding="utf-8")

    print(f"미리보기 : {page_path}")
    print(f"사진 폴더 : {images_dir}  ({len(exported)}장)")
    if resolution.problems:
        print(f"\n확인 필요 {len(resolution.problems)}건:")
        for slot in resolution.problems:
            print(f"  - 사진 {slot.number}: {slot.problem}")
    if resolution.unused_photos:
        print(f"\n글에 안 쓰인 사진 {len(resolution.unused_photos)}장:")
        for photo in resolution.unused_photos:
            print(f"  - {photo.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
